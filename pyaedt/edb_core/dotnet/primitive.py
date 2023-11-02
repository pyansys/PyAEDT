"""Primitive."""
from pyaedt.edb_core.dotnet.database import NetDotNet, PolygonDataDotNet
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.modeler.geometry_operators import GeometryOperators


def cast(api, prim_object):
    """Cast the primitive object to correct concrete type.

    Returns
    -------
    PrimitiveDotNet
    """
    prim_type = prim_object.GetPrimitiveType()
    if prim_type == prim_type.Rectangle:
        return RectangleDotNet(api, prim_object)
    elif prim_type == prim_type.Polygon:
        return PolygonDotNet(api, prim_object)
    elif prim_type == prim_type.Path:
        return PathDotNet(api, prim_object)
    elif prim_type == prim_type.Bondwire:
        return BondwireDotNet(api, prim_object)
    elif prim_type == prim_type.Text:
        return TextDotNet(api, prim_object)
    elif prim_type == prim_type.Circle:
        return CircleDotNet(api, prim_object)
    else:
        return None


class PrimitiveDotNet:
    """Base class representing primitive objects."""

    def __getattr__(self, key):
        try:
            return super().__getattribute__(key)
        except AttributeError:
            if self.prim_obj and key in dir(self.prim_obj):
                obj = self.prim_obj
            else:
                obj = self.api
            try:
                return getattr(obj, key)
            except AttributeError:  # pragma: no cover
                raise AttributeError("Attribute {} not present".format(key))

    def __init__(self, api, prim_object=None):
        self._app = api
        self.api = api._edb.Cell.Primitive
        self.edb_api = api._edb
        self.prim_obj = prim_object

    @property
    def api_class(self):
        return self.api

    @property
    def api_object(self):
        return self.prim_obj

    @property
    def path(self):
        return PathDotNet(self._app)

    @property
    def rectangle(self):
        return RectangleDotNet(self._app)

    @property
    def circle(self):
        return CircleDotNet(self._app)

    @property
    def polygon(self):
        return PolygonDotNet(self._app)

    @property
    def text(self):
        return TextDotNet(self._app)

    @property
    def bondwire(self):
        return BondwireDotNet(self._app)

    @property
    def padstack_instance(self):
        return PadstackInstanceDotNet(self._app)

    @property
    def net(self):
        return self.prim_obj.GetNet()

    @net.setter
    def net(self, value):
        try:
            if "net" in dir(value):
                self.prim_obj.SetNet(value.net_obj)
            else:
                self.prim_obj.SetNet(value)
        except TypeError:
            self._app.logger.error("Error setting net object")

    @property
    def polygon_data(self):
        """:class:`pyaedt.edb_core.dotnet.database.PolygonDataDotNet`: Outer contour of the Polygon object."""
        return PolygonDataDotNet(self._app, self.prim_obj.GetPolygonData())

    @polygon_data.setter
    def polygon_data(self, poly):
        return self.prim_obj.SetPolygonData(poly)

    @property
    def primitive_type(self):
        """:class:`PrimitiveType`: Primitive type of the primitive.

        Read-Only.
        """
        return self.prim_obj.GetPrimitiveType()

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
            point_list = self._app.edb_api.cell.primitive.polygon.create(
                self._app.active_layout, self.layer_name, self.prim_obj.GetNet(), _poly
            ).prim_obj
        elif "prim_obj" in dir(point_list):
            point_list = point_list.prim_obj
        elif "primitive_obj" in dir(point_list):
            point_list = point_list.primitive_obj
        return self.prim_obj.AddVoid(point_list)

    def set_hfss_prop(self, material, solve_inside):
        """Set HFSS properties.

        Parameters
        ----------
        material : str
            Material property name to be set.
        solve_inside : bool
            Whether to do solve inside.
        """
        self.prim_obj.SetHfssProp(material, solve_inside)

    @property
    def layer(self):
        """:class:`Layer <ansys.edb.layer.Layer>`: Layer that the primitive object is on."""
        layer_msg = self.prim_obj.GetLayer()
        return layer_msg

    @layer.setter
    def layer(self, layer):
        self.prim_obj.SetLayer(layer)

    @property
    def is_negative(self):
        """:obj:`bool`: If the primitive is negative."""
        return self.prim_obj.GetIsNegative()

    @is_negative.setter
    def is_negative(self, is_negative):
        self.prim_obj.SetIsNegative(is_negative)

    @property
    def is_void(self):
        """:obj:`bool`: If a primitive is a void."""
        return self.prim_obj.IsVoid()

    @property
    def has_voids(self):
        """:obj:`bool`: If a primitive has voids inside.

        Read-Only.
        """
        return self.prim_obj.HasVoids()

    @property
    def voids(self):
        """:obj:`list` of :class:`Primitive <ansys.edb.primitive.Primitive>`: List of void\
        primitive objects inside the primitive.

        Read-Only.
        """
        return [cast(self._app, void) for void in self.prim_obj.Voids]

    @property
    def owner(self):
        """:class:`Primitive <ansys.edb.primitive.Primitive>`: Owner of the primitive object.

        Read-Only.
        """
        return cast(self._app, self.prim_obj)

    @property
    def is_parameterized(self):
        """:obj:`bool`: Primitive's parametrization.

        Read-Only.
        """
        return self.prim_obj.IsParameterized()

    def get_hfss_prop(self):
        """Get HFSS properties.

        Returns
        -------
        material : str
            Material property name.
        solve_inside : bool
            If solve inside.
        """
        material = ""
        solve_inside = True
        self.prim_obj.GetHfssProp(material, solve_inside)
        return material, solve_inside

    def remove_hfss_prop(self):
        """Remove HFSS properties."""
        self.prim_obj.RemoveHfssProp()

    @property
    def is_zone_primitive(self):
        """:obj:`bool`: If primitive object is a zone.

        Read-Only.
        """
        return self.prim_obj.IsZonePrimitive()

    @property
    def can_be_zone_primitive(self):
        """:obj:`bool`: If a primitive can be a zone.

        Read-Only.
        """
        return True

    def make_zone_primitive(self, zone_id):
        """Make primitive a zone primitive with a zone specified by the provided id.

        Parameters
        ----------
        zone_id : int
            Id of zone primitive will use.

        """
        self.prim_obj.MakeZonePrimitive(zone_id)

    def _get_points_for_plot(self, my_net_points, num):
        """Get the points to be plot
        """
        # fmt: off
        x = []
        y = []
        for i, point in enumerate(my_net_points):
            # point = my_net_points[i]
            if not point.IsArc():
                x.append(point.X.ToDouble())
                y.append(point.Y.ToDouble())
                # i += 1
            else:
                arc_h = point.GetArcHeight().ToDouble()
                p1 = [my_net_points[i-1].X.ToDouble(), my_net_points[i-1].Y.ToDouble()]
                if i+1 < len(my_net_points):
                    p2 = [my_net_points[i+1].X.ToDouble(), my_net_points[i+1].Y.ToDouble()]
                else:
                    p2 = [my_net_points[0].X.ToDouble(), my_net_points[0].Y.ToDouble()]
                x_arc, y_arc = self._eval_arc_points(p1, p2, arc_h, num)
                x.extend(x_arc)
                y.extend(y_arc)
                # i += 1
        # fmt: on
        return x, y

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
            my_net_points = list(self.prim_obj.GetPolygonData().Points)
            xt, yt = self._get_points_for_plot(my_net_points, arc_segments)
            if not xt:
                return []
            x, y = GeometryOperators.orient_polygon(xt, yt, clockwise=True)
            return x, y
        except:
            x = []
            y = []
        return x, y

    def points_raw(self):
        """Return a list of Edb points.

        Returns
        -------
        list
            Edb Points.
        """
        points = []
        try:
            my_net_points = list(self.prim_obj.GetPolygonData().Points)
            for point in my_net_points:
                points.append(point)
            return points
        except:
            return points


class RectangleDotNet(PrimitiveDotNet):
    """Class representing a rectangle object."""

    def __init__(self, api, prim_obj=None):
        PrimitiveDotNet.__init__(self, api, prim_obj)

    def create(self, layout, layer, net, rep_type, param1, param2, param3, param4, corner_rad, rotation):
        """Create a rectangle.

        Parameters
        ----------
        layout : :class:`Layout <ansys.edb.layout.Layout>`
            Layout this rectangle will be in.
        layer : str or :class:`Layer <ansys.edb.layer.Layer>`
            Layer this rectangle will be on.
        net : str or :class:`Net <ansys.edb.net.Net>` or None
            Net this rectangle will have.
        rep_type : :class:`RectangleRepresentationType`
            Type that defines given parameters meaning.
        param1 : :class:`Value <ansys.edb.utility.Value>`
            X value of lower left point or center point.
        param2 : :class:`Value <ansys.edb.utility.Value>`
            Y value of lower left point or center point.
        param3 : :class:`Value <ansys.edb.utility.Value>`
            X value of upper right point or width.
        param4 : :class:`Value <ansys.edb.utility.Value>`
            Y value of upper right point or height.
        corner_rad : :class:`Value <ansys.edb.utility.Value>`
            Corner radius.
        rotation : :class:`Value <ansys.edb.utility.Value>`
            Rotation.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.primitive.RectangleDotNet`

            Rectangle that was created.
        """
        if isinstance(net, NetDotNet):
            net = net.api_object
        if isinstance(rep_type, int):
            if rep_type == 1:
                rep_type = self.edb_api.cell.primitive.RectangleRepresentationType.CenterWidthHeight
            else:
                rep_type = self.edb_api.cell.primitive.RectangleRepresentationType.LowerLeftUpperRight
        param1 = self._app.edb_api.utility.value(param1)
        param2 = self._app.edb_api.utility.value(param2)
        param3 = self._app.edb_api.utility.value(param3)
        param4 = self._app.edb_api.utility.value(param4)
        corner_rad = self._app.edb_api.utility.value(corner_rad)
        rotation = self._app.edb_api.utility.value(rotation)
        return RectangleDotNet(
            self._app,
            self.api.Rectangle.Create(
                layout, layer, net, rep_type, param1, param2, param3, param4, corner_rad, rotation
            ),
        )

    def get_parameters(self):
        """Get coordinates parameters.

        Returns
        -------
        tuple[
            :class:`RectangleRepresentationType`,
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`
        ]

            Returns a tuple of the following format:

            **(representation_type, parameter1, parameter2, parameter3, parameter4, corner_radius, rotation)**

            **representation_type** : Type that defines given parameters meaning.

            **parameter1** : X value of lower left point or center point.

            **parameter2** : Y value of lower left point or center point.

            **parameter3** : X value of upper right point or width.

            **parameter4** : Y value of upper right point or height.

            **corner_radius** : Corner radius.

            **rotation** : Rotation.
        """
        return self.prim_obj.GetParameters()

    def set_parameters(self, rep_type, param1, param2, param3, param4, corner_rad, rotation):
        """Set coordinates parameters.

        Parameters
        ----------
        rep_type : :class:`RectangleRepresentationType`
            Type that defines given parameters meaning.
        param1 : :class:`Value <ansys.edb.utility.Value>`
            X value of lower left point or center point.
        param2 : :class:`Value <ansys.edb.utility.Value>`
            Y value of lower left point or center point.
        param3 : :class:`Value <ansys.edb.utility.Value>`
            X value of upper right point or width.
        param4 : :class:`Value <ansys.edb.utility.Value>`
            Y value of upper right point or height.
        corner_rad : :class:`Value <ansys.edb.utility.Value>`
            Corner radius.
        rotation : :class:`Value <ansys.edb.utility.Value>`
            Rotation.
        """
        return self.prim_obj.SetParameters(
            rep_type,
            param1,
            param2,
            param3,
            param4,
            corner_rad,
            rotation,
        )

    @property
    def can_be_zone_primitive(self):
        """:obj:`bool`: If a rectangle can be a zone.

        Read-Only.
        """
        return True


class CircleDotNet(PrimitiveDotNet):
    """Class representing a circle object."""

    def __init__(self, api, prim_obj=None):
        PrimitiveDotNet.__init__(self, api, prim_obj)

    def create(self, layout, layer, net, center_x, center_y, radius):
        """Create a circle.

        Parameters
        ----------
        layout: :class:`Layout <ansys.edb.layout.Layout>`
            Layout this circle will be in.
        layer: str or :class:`Layer <ansys.edb.layer.Layer>`
            Layer this circle will be on.
        net: str or :class:`Net <ansys.edb.net.Net>` or None
            Net this circle will have.
        center_x: :class:`Value <ansys.edb.utility.Value>`
            X value of center point.
        center_y: :class:`Value <ansys.edb.utility.Value>`
            Y value of center point.
        radius: :class:`Value <ansys.edb.utility.Value>`
            Radius value of the circle.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.primitive.CircleDotNet`
            Circle object created.
        """
        if isinstance(net, NetDotNet):
            net = net.api_object
        return CircleDotNet(
            self._app,
            self.api.Circle.Create(
                layout,
                layer,
                net,
                center_x,
                center_y,
                radius,
            ),
        )

    def get_parameters(self):
        """Get parameters of a circle.

        Returns
        -------
        tuple[
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`
        ]

            Returns a tuple of the following format:

            **(center_x, center_y, radius)**

            **center_x** : X value of center point.

            **center_y** : Y value of center point.

            **radius** : Radius value of the circle.
        """
        return self.prim_obj.GetParameters()

    def set_parameters(self, center_x, center_y, radius):
        """Set parameters of a circle.

        Parameters
        ----------
        center_x: :class:`Value <ansys.edb.utility.Value>`
            X value of center point.
        center_y: :class:`Value <ansys.edb.utility.Value>`
            Y value of center point.
        radius: :class:`Value <ansys.edb.utility.Value>`
            Radius value of the circle.
        """
        self.prim_obj.SetParameters(
            center_x,
            center_y,
            radius,
        )

    def get_polygon_data(self):
        """:class:`PolygonData <ansys.edb.geometry.PolygonData>`: Polygon data object of the Circle object."""
        return self.prim_obj.GetPolygonData()

    def can_be_zone_primitive(self):
        """:obj:`bool`: If a circle can be a zone."""
        return True


class TextDotNet(PrimitiveDotNet):
    """Class representing a text object."""

    def __init__(self, api, prim_obj=None):
        PrimitiveDotNet.__init__(self, api, prim_obj)

    def create(self, layout, layer, center_x, center_y, text):
        """Create a text object.

        Parameters
        ----------
        layout: :class:`Layout <ansys.edb.layout.Layout>`
            Layout this text will be in.
        layer: str or Layer
            Layer this text will be on.
        center_x: :class:`Value <ansys.edb.utility.Value>`
            X value of center point.
        center_y: :class:`Value <ansys.edb.utility.Value>`
            Y value of center point.
        text: str
            Text string.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.primitive.TextDotNet`
            The text Object that was created.
        """
        return TextDotNet(
            self._app,
            self.api.Text.Create(
                layout,
                layer,
                center_x,
                center_y,
                text,
            ),
        )

    def get_text_data(self):
        """Get the text data of a text.

        Returns
        -------
        tuple[
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`,
            str
        ]
            Returns a tuple of the following format:

            **(center_x, center_y, text)**

            **center_x** : X value of center point.

            **center_y** : Y value of center point.

            **radius** : Text object's String value.
        """
        return self.prim_obj.GetTextData()

    def set_text_data(self, center_x, center_y, text):
        """Set the text data of a text.

        Parameters
        ----------
        center_x: :class:`Value <ansys.edb.utility.Value>`
            X value of center point.
        center_y: :class:`Value <ansys.edb.utility.Value>`
            Y value of center point.
        text: str
            Text object's String value.
        """
        return self.prim_obj.SetTextData(
            center_x,
            center_y,
            text,
        )


class PolygonDotNet(PrimitiveDotNet):
    """Class representing a polygon object."""

    def __init__(self, api, prim_obj=None):
        PrimitiveDotNet.__init__(self, api, prim_obj)

    def create(self, layout, layer, net, polygon_data):
        """Create a polygon.

        Parameters
        ----------
        layout : :class:`Layout <ansys.edb.layout.Layout>`
            Layout the polygon will be in.
        layer : str or :class:`Layer <ansys.edb.layer.Layer>`
            Layer this Polygon will be in.
        net : str or :class:`Net <ansys.edb.net.Net>` or None
            Net of the Polygon object.
        polygon_data : :class:`PolygonData <ansys.edb.geometry.PolygonData>`
            The outer contour of the Polygon.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.primitive.PolygonDotNet`
            Polygon object created.
        """
        if isinstance(net, NetDotNet):
            net = net.api_object
        return PolygonDotNet(self._app, self.api.Polygon.Create(layout, layer, net, polygon_data))

    @property
    def can_be_zone_primitive(self):
        """:obj:`bool`: If a polygon can be a zone.

        Read-Only.
        """
        return True


class PathDotNet(PrimitiveDotNet):
    """Class representing a path object."""

    def __init__(self, api, prim_obj=None):
        PrimitiveDotNet.__init__(self, api, prim_obj)

    def create(self, layout, layer, net, width, end_cap1, end_cap2, corner_style, points):
        """Create a path.

        Parameters
        ----------
        layout : :class:`Layout <ansys.edb.layout.Layout>`
            Layout this Path will be in.
        layer : str or :class:`Layer <ansys.edb.layer.Layer>`
            Layer this Path will be on.
        net : str or :class:`Net <ansys.edb.net.Net>` or None
            Net this Path will have.
        width: :class:`Value <ansys.edb.utility.Value>`
            Path width.
        end_cap1: :class:`PathEndCapType`
            End cap style of path start end cap.
        end_cap2: :class:`PathEndCapType`
            End cap style of path end end cap.
        corner_style: :class:`PathCornerType`
            Corner style.
        points : :class:`PolygonData <ansys.edb.geometry.PolygonData>` or center line point list.
            Centerline polygonData to set.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.primitive.PathDotNet`
            Path object created.
        """
        if isinstance(net, NetDotNet):
            net = net.api_object
        width = self._app.edb_api.utility.value(width)
        if isinstance(points, list):
            points = self._app.edb_api.geometry.polygon_data.api_class(
                convert_py_list_to_net_list([self._app.geometry.point_data(i) for i in points]), False
            )
        return PathDotNet(
            self._app, self.api.Path.Create(layout, layer, net, width, end_cap1, end_cap2, corner_style, points)
        )

    @property
    def center_line(self):
        """:class:`PolygonData <ansys.edb.geometry.PolygonData>`: Center line for this Path."""
        return self.prim_obj.GetCenterLine()

    @center_line.setter
    def center_line(self, center_line):
        self.prim_obj.SetCenterLineMessage(center_line)

    @property
    def end_cap_style(self):
        """Get path end cap styles.

        Returns
        -------
        tuple[
            :class:`PathEndCapType`,
            :class:`PathEndCapType`
        ]

            Returns a tuple of the following format:

            **(end_cap1, end_cap2)**

            **end_cap1** : End cap style of path start end cap.

            **end_cap2** : End cap style of path end end cap.
        """
        return self._edb_object.GetEndCapStyle()

    @end_cap_style.setter
    def end_cap_style(self, end_cap1, end_cap2):
        """Set path end cap styles.

        Parameters
        ----------
        end_cap1: :class:`PathEndCapType`
            End cap style of path start end cap.
        end_cap2: :class:`PathEndCapType`
            End cap style of path end end cap.
        """
        self._edb_object.SetEndCapStyle(end_cap1, end_cap2)

    @property
    def get_clip_info(self):
        """Get data used to clip the path.

        Returns
        -------
        tuple[:class:`PolygonData <ansys.edb.geometry.PolygonData>`, bool]

            Returns a tuple of the following format:

            **(clipping_poly, keep_inside)**

            **clipping_poly** : PolygonData used to clip the path.

            **keep_inside** : Indicates whether the part of the path inside the polygon is preserved.
        """
        return self._edb_object.GetClipInfo()

    @get_clip_info.setter
    def get_clip_info(self, clipping_poly, keep_inside=True):
        """Set data used to clip the path.

        Parameters
        ----------
        clipping_poly: :class:`PolygonData <ansys.edb.geometry.PolygonData>`
            PolygonData used to clip the path.
        keep_inside: bool
            Indicates whether the part of the path inside the polygon should be preserved.
        """
        self._edb_object.SetClipInfo(
            clipping_poly,
            keep_inside,
        )

    @property
    def corner_style(self):
        """:class:`PathCornerType`: Path's corner style."""
        return self.prim_obj.GetCornerStyle()

    @corner_style.setter
    def corner_style(self, corner_type):
        self.prim_obj.SetCornerStyle(corner_type)

    @property
    def width(self):
        """:class:`Value <ansys.edb.utility.Value>`: Path width."""
        return self.prim_obj.GetWidth()

    @width.setter
    def width(self, width):
        self.prim_obj.SetWidth(width)

    @property
    def miter_ratio(self):
        """:class:`Value <ansys.edb.utility.Value>`: Miter ratio."""
        return self.prim_obj.GetMiterRatio()

    @miter_ratio.setter
    def miter_ratio(self, miter_ratio):
        self.prim_obj.SetMiterRatio(miter_ratio)

    @property
    def can_be_zone_primitive(self):
        """:obj:`bool`: If a path can be a zone.

        Read-Only.
        """
        return True


class BondwireDotNet(PrimitiveDotNet):
    """Class representing a bondwire object."""

    def __init__(self, api, prim_obj=None):
        PrimitiveDotNet.__init__(self, api, prim_obj)

    def create(
        self,
        layout,
        bondwire_type,
        definition_name,
        placement_layer,
        width,
        material,
        start_context,
        start_layer_name,
        start_x,
        start_y,
        end_context,
        end_layer_name,
        end_x,
        end_y,
        net,
    ):
        """Create a bondwire object.

        Parameters
        ----------
        layout : :class:`Layout <ansys.edb.layout.Layout>`
            Layout this bondwire will be in.
        bondwire_type : :class:`BondwireType`
            Type of bondwire: kAPDBondWire or kJDECBondWire types.
        definition_name : str
            Bondwire definition name.
        placement_layer : str
            Layer name this bondwire will be on.
        width : :class:`Value <ansys.edb.utility.Value>`
            Bondwire width.
        material : str
            Bondwire material name.
        start_context : :class:`CellInstance <ansys.edb.hierarchy.CellInstance>`
            Start context: None means top level.
        start_layer_name : str
            Name of start layer.
        start_x : :class:`Value <ansys.edb.utility.Value>`
            X value of start point.
        start_y : :class:`Value <ansys.edb.utility.Value>`
            Y value of start point.
        end_context : :class:`CellInstance <ansys.edb.hierarchy.CellInstance>`
            End context: None means top level.
        end_layer_name : str
            Name of end layer.
        end_x : :class:`Value <ansys.edb.utility.Value>`
            X value of end point.
        end_y : :class:`Value <ansys.edb.utility.Value>`
            Y value of end point.
        net : str or :class:`Net <ansys.edb.net.Net>` or None
            Net of the Bondwire.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.primitive.BondwireDotNet`
            Bondwire object created.
        """
        if isinstance(net, NetDotNet):
            net = net.api_object
        return BondwireDotNet(
            self._app,
            self.api.Bondwire.Create(
                layout,
                net,
                bondwire_type,
                definition_name,
                placement_layer,
                width,
                material,
                start_context,
                start_layer_name,
                start_x,
                start_y,
                end_context,
                end_layer_name,
                end_x,
                end_y,
            ),
        )

    def get_material(self, evaluated=True):
        """Get material of the bondwire.

        Parameters
        ----------
        evaluated : bool, optional
            True if an evaluated material name is wanted.

        Returns
        -------
        str
            Material name.
        """
        return self.prim_obj.GetMaterial(evaluated)

    def set_material(self, material):
        """Set the material of a bondwire.

        Parameters
        ----------
        material : str
            Material name.
        """
        self.prim_obj.SetMaterial(material)

    @property
    def type(self):
        """:class:`BondwireType`: Bondwire-type of a bondwire object."""
        return self.prim_obj.GetType()

    @type.setter
    def type(self, bondwire_type):
        self.prim_obj.SetType(bondwire_type)

    @property
    def cross_section_type(self):
        """:class:`BondwireCrossSectionType`: Bondwire-cross-section-type of a bondwire object."""
        return self.prim_obj.GetCrossSectionType()

    @cross_section_type.setter
    def cross_section_type(self, bondwire_type):
        self.prim_obj.SetCrossSectionType(bondwire_type)

    @property
    def cross_section_height(self):
        """:class:`Value <ansys.edb.utility.Value>`: Bondwire-cross-section height of a bondwire object."""
        return self.prim_obj.GetCrossSectionHeight()

    @cross_section_height.setter
    def cross_section_height(self, height):
        self.prim_obj.SetCrossSectionHeight(height)

    def get_definition_name(self, evaluated=True):
        """Get definition name of a bondwire object.

        Parameters
        ----------
        evaluated : bool, optional
            True if an evaluated (in variable namespace) material name is wanted.

        Returns
        -------
        str
            Bondwire name.
        """
        return self.prim_obj.GetDefinitionName(evaluated)

    def set_definition_name(self, definition_name):
        """Set the definition name of a bondwire.

        Parameters
        ----------
        definition_name : str
            Bondwire name to be set.
        """
        self.prim_obj.SetDefinitionName(definition_name)

    def get_traj(self):
        """Get trajectory parameters of a bondwire object.

        Returns
        -------
        tuple[
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`
        ]

            Returns a tuple of the following format:

            **(x1, y1, x2, y2)**

            **x1** : X value of the start point.

            **y1** : Y value of the start point.

            **x1** : X value of the end point.

            **y1** : Y value of the end point.
        """
        return self.prim_obj.GetTraj()

    def set_traj(self, x1, y1, x2, y2):
        """Set the parameters of the trajectory of a bondwire.

        Parameters
        ----------
        x1 : :class:`Value <ansys.edb.utility.Value>`
            X value of the start point.
        y1 : :class:`Value <ansys.edb.utility.Value>`
            Y value of the start point.
        x2 : :class:`Value <ansys.edb.utility.Value>`
            X value of the end point.
        y2 : :class:`Value <ansys.edb.utility.Value>`
            Y value of the end point.
        """
        self.prim_obj.SetTraj(x1, y1, x2, y2)

    @property
    def width(self):
        """:class:`Value <ansys.edb.utility.Value>`: Width of a bondwire object."""
        return self.prim_obj.GetWidthValue()

    @width.setter
    def width(self, width):
        self.prim_obj.SetWidthValue(width)

    def get_start_elevation(self, start_context):
        """Get the start elevation layer of a bondwire object.

        Parameters
        ----------
        start_context : :class:`CellInstance <ansys.edb.hierarchy.CellInstance>`
            Start cell context of the bondwire.

        Returns
        -------
        :class:`Layer <ansys.edb.layer.Layer>`
            Start context of the bondwire.
        """
        return self.prim_obj.GetStartElevation(start_context)

    def set_start_elevation(self, start_context, layer):
        """Set the start elevation of a bondwire.

        Parameters
        ----------
        start_context : :class:`CellInstance <ansys.edb.hierarchy.CellInstance>`
            Start cell context of the bondwire. None means top level.
        layer : str or :class:`Layer <ansys.edb.layer.Layer>`
            Start layer of the bondwire.
        """
        self.prim_obj.SetStartElevation(start_context, layer)

    def get_end_elevation(self, end_context):
        """Get the end elevation layer of a bondwire object.

        Parameters
        ----------
        end_context : :class:`CellInstance <ansys.edb.hierarchy.CellInstance>`
            End cell context of the bondwire.

        Returns
        -------
        :class:`Layer <ansys.edb.layer.Layer>`
            End context of the bondwire.
        """
        return self.prim_obj.GetEndElevation(end_context)

    def set_end_elevation(self, end_context, layer):
        """Set the end elevation of a bondwire.

        Parameters
        ----------
        end_context : :class:`CellInstance <ansys.edb.hierarchy.CellInstance>`
            End cell context of the bondwire. None means top level.
        layer : str or :class:`Layer <ansys.edb.layer.Layer>`
            End layer of the bondwire.
        """
        self.prim_obj.SetEndElevation(end_context, layer)


class PadstackInstanceDotNet(PrimitiveDotNet):
    """Class representing a Padstack Instance object."""

    def __init__(self, api, prim_obj=None):
        PrimitiveDotNet.__init__(self, api, prim_obj)

    def create(
        self,
        layout,
        net,
        name,
        padstack_def,
        point,
        rotation,
        top_layer,
        bottom_layer,
        solder_ball_layer,
        layer_map,
    ):
        """Create a PadstackInstance object.

        Parameters
        ----------
        layout : :class:`Layout <ansys.edb.layout.Layout>`
            Layout this padstack instance will be in.
        net : :class:`Net <ansys.edb.net.Net>`
            Net of this padstack instance.
        name : str
            Name of padstack instance.
        padstack_def : PadstackDef
            Padstack definition of this padstack instance.
        rotation : :class:`Value <ansys.edb.utility.Value>`
            Rotation of this padstack instance.
        top_layer : :class:`Layer <ansys.edb.layer.Layer>`
            Top layer of this padstack instance.
        bottom_layer : :class:`Layer <ansys.edb.layer.Layer>`
            Bottom layer of this padstack instance.
        solder_ball_layer : :class:`Layer <ansys.edb.layer.Layer>`
            Solder ball layer of this padstack instance, or None for none.
        layer_map : :class:`LayerMap <ansys.edb.utility.LayerMap>`
            Layer map of this padstack instance. None or empty means do auto-mapping.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.primitive.PadstackInstanceDotNet`
            Padstack instance object created.
        """
        if isinstance(net, NetDotNet):
            net = net.api_object
        if isinstance(point, list):
            point = self._app.geometry.point_data(point[0], point[1])
        return PadstackInstanceDotNet(
            self._app,
            self.api.PadstackInstance.Create(
                layout,
                net,
                name,
                padstack_def,
                point,
                rotation,
                top_layer,
                bottom_layer,
                solder_ball_layer,
                layer_map,
            ),
        )

    @property
    def padstack_def(self):
        """:class:`PadstackDef <ansys.edb.definition.padstack_def>`: PadstackDef of a Padstack Instance."""
        return self.prim_obj.GetPadstackDef()

    @property
    def name(self):
        """:obj:`str`: Name of a Padstack Instance."""
        return self.prim_obj.GetName()

    @name.setter
    def name(self, name):
        self.prim_obj.SetName(name)

    def get_position_and_rotation(self):
        """Get the position and rotation of a Padstack Instance.

        Returns
        -------
        tuple[
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`
        ]

            Returns a tuple of the following format:

            **(x, y, rotation)**

            **x** : X coordinate.

            **y** : Y coordinate.

            **rotation** : Rotation in radians.
        """
        return self.prim_obj.GetPositionAndRotation()

    def set_position_and_rotation(self, x, y, rotation):
        """Set the position and rotation of a Padstack Instance.

        Parameters
        ----------
        x : :class:`Value <ansys.edb.utility.Value>`
            x : X coordinate.
        y : :class:`Value <ansys.edb.utility.Value>`
            y : Y coordinate.
        rotation : :class:`Value <ansys.edb.utility.Value>`
            rotation : Rotation in radians.
        """
        self.prim_obj.SetPositionAndRotation(x, y, rotation)

    def get_layer_range(self):
        """Get the top and bottom layers of a Padstack Instance.

        Returns
        -------
        tuple[
            :class:`Layer <ansys.edb.layer.Layer>`,
            :class:`Layer <ansys.edb.layer.Layer>`
        ]

            Returns a tuple of the following format:

            **(top_layer, bottom_layer)**

            **top_layer** : Top layer of the Padstack instance

            **bottom_layer** : Bottom layer of the Padstack instance
        """
        return self.prim_obj.GetLayerRange()

    def set_layer_range(self, top_layer, bottom_layer):
        """Set the top and bottom layers of a Padstack Instance.

        Parameters
        ----------
        top_layer : :class:`Layer <ansys.edb.layer.Layer>`
            Top layer of the Padstack instance.
        bottom_layer : :class:`Layer <ansys.edb.layer.Layer>`
            Bottom layer of the Padstack instance.
        """
        self.prim_obj.SetLayerRange(top_layer, bottom_layer)

    @property
    def solderball_layer(self):
        """:class:`Layer <ansys.edb.layer.Layer>`: SolderBall Layer of Padstack Instance."""
        return self.prim_obj.GetSolderBallLayer()

    @solderball_layer.setter
    def solderball_layer(self, solderball_layer):
        self.prim_obj.SetSolderBallLayer(solderball_layer)

    @property
    def layer_map(self):
        """:class:`LayerMap <ansys.edb.utility.LayerMap>`: Layer Map of the Padstack Instance."""
        return self.prim_obj.GetLayerMap()

    @layer_map.setter
    def layer_map(self, layer_map):
        self.prim_obj.SetLayerMap(layer_map)

    def get_hole_overrides(self):
        """Get the hole overrides of Padstack Instance.

        Returns
        -------
        tuple[
            bool,
            :class:`Value <ansys.edb.utility.Value>`
        ]

            Returns a tuple of the following format:

            **(is_hole_override, hole_override)**

            **is_hole_override** : If padstack instance is hole override.

            **hole_override** : Hole override diameter of this padstack instance.
        """
        return self.prim_obj.GetHoleOverrides()

    def set_hole_overrides(self, is_hole_override, hole_override):
        """Set the hole overrides of Padstack Instance.

        Parameters
        ----------
        is_hole_override : bool
            If padstack instance is hole override.
        hole_override : :class:`Value <ansys.edb.utility.Value>`
            Hole override diameter of this padstack instance.
        """
        self.prim_obj.SetHoleOverrides(is_hole_override, hole_override)

    @property
    def is_layout_pin(self):
        """:obj:`bool`: If padstack instance is layout pin."""
        return self.prim_obj.GetIsLayoutPin()

    @is_layout_pin.setter
    def is_layout_pin(self, is_layout_pin):
        self.prim_obj.SetIsLayoutPin(is_layout_pin)

    def get_back_drill_type(self, from_bottom):
        """Get the back drill type of Padstack Instance.

        Parameters
        ----------
        from_bottom : bool
            True to get drill type from bottom.

        Returns
        -------
        :class:`BackDrillType`
            Back-Drill Type of padastack instance.
        """
        return self.prim_obj.GetBackDrillType(from_bottom)

    def get_back_drill_by_layer(self, from_bottom):
        """Get the back drill by layer.

        Parameters
        ----------
        from_bottom : bool
            True to get drill type from bottom.

        Returns
        -------
        tuple[
            bool,
            :class:`Value <ansys.edb.utility.Value>`,
            :class:`Value <ansys.edb.utility.Value>`
        ]

            Returns a tuple of the following format:

            **(drill_to_layer, offset, diameter)**

            **drill_to_layer** : Layer drills to. If drill from top, drill stops at the upper elevation of the layer.\
            If from bottom, drill stops at the lower elevation of the layer.

            **offset** : Layer offset (or depth if layer is empty).

            **diameter** : Drilling diameter.
        """
        return self.prim_obj.GetBackDrillByLayer(from_bottom)

    def set_back_drill_by_layer(self, drill_to_layer, offset, diameter, from_bottom):
        """Set the back drill by layer.

        Parameters
        ----------
        drill_to_layer : :class:`Layer <ansys.edb.layer.Layer>`
            Layer drills to. If drill from top, drill stops at the upper elevation of the layer.
            If from bottom, drill stops at the lower elevation of the layer.
        offset : :class:`Value <ansys.edb.utility.Value>`
            Layer offset (or depth if layer is empty).
        diameter : :class:`Value <ansys.edb.utility.Value>`
            Drilling diameter.
        from_bottom : bool
            True to set drill type from bottom.
        """
        self.prim_obj.SetBackDrillByLayer(drill_to_layer, offset, diameter, from_bottom)

    def get_back_drill_by_depth(self, from_bottom):
        """Get the back drill by depth.

        Parameters
        ----------
        from_bottom : bool
            True to get drill type from bottom.

        Returns
        -------
        tuple[
            bool,
            :class:`Value <ansys.edb.utility.Value>`
        ]
            Returns a tuple of the following format:

            **(drill_depth, diameter)**

            **drill_depth** : Drilling depth, may not align with layer.

            **diameter** : Drilling diameter.
        """
        return self.prim_obj.GetBackDrillByDepth(from_bottom)

    def set_back_drill_by_depth(self, drill_depth, diameter, from_bottom):
        """Set the back drill by Depth.

        Parameters
        ----------
        drill_depth : :class:`Value <ansys.edb.utility.Value>`
            Drilling depth, may not align with layer.
        diameter : :class:`Value <ansys.edb.utility.Value>`
            Drilling diameter.
        from_bottom : bool
            True to set drill type from bottom.
        """
        self.prim_obj.SetBackDrillByDepth(drill_depth, diameter, from_bottom)

    def get_padstack_instance_terminal(self):
        """:class:`TerminalInstance <ansys.edb.terminal.TerminalInstance>`: Padstack Instance's terminal."""
        return self.prim_obj.GetPadstackInstanceTerminal()

    def is_in_pin_group(self, pin_group):
        """Check if Padstack instance is in the Pin Group.

        Parameters
        ----------
        pin_group : :class:`PinGroup <ansys.edb.hierarchy.PinGroup>`
            Pin group to check if padstack instance is in.

        Returns
        -------
        bool
            True if padstack instance is in pin group.
        """
        return self.prim_obj.IsInPinGroup(pin_group)

    @property
    def pin_groups(self):
        """:obj:`list` of :class:`PinGroup <ansys.edb.hierarchy.PinGroup>`: Pin groups of Padstack instance object.

        Read-Only.
        """
        return self.prim_obj.GetPinGroups()


class BoardBendDef(PrimitiveDotNet):
    """Class representing board bending definitions."""

    def __init__(self, api, prim_obj=None):
        PrimitiveDotNet.__init__(self, api, prim_obj)

    def create(self, zone_prim, bend_middle, bend_radius, bend_angle):
        """Create a board bend definition.

        Parameters
        ----------
        zone_prim : :class:`Primitive <Primitive>`
            Zone primitive this board bend definition exists on.
        bend_middle : :term:`PointDataTuple`
            Tuple containing the starting and ending points of the line that represents the middle of the bend.
        bend_radius : :term:`ValueLike`
            Radius of the bend.
        bend_angle : :term:`ValueLike`
            Angle of the bend.

        Returns
        -------
        BoardBendDef
            BoardBendDef that was created.
        """
        return BoardBendDef(
            self._app,
            self.api.BoardBendDef.Create(
                zone_prim,
                bend_middle,
                bend_radius,
                bend_angle,
            ),
        )

    @property
    def boundary_primitive(self):
        """:class:`Primitive <Primitive>`: Zone primitive the board bend is placed on.

        Read-Only.
        """
        return cast(self.edb_api, self.prim_obj.GetBoundaryPrim())

    @property
    def bend_middle(self):
        """:term:`PointDataTuple`: Tuple of the bend middle starting and ending points."""
        return self.prim_obj.GetBendMiddle()

    @bend_middle.setter
    def bend_middle(self, bend_middle):
        self.prim_obj.SetBendMiddle(bend_middle)

    @property
    def radius(self):
        """:term:`ValueLike`: Radius of the bend."""
        return self.prim_obj.GetRadius()

    @radius.setter
    def radius(self, val):
        self.prim_obj.SetRadius(val)

    @property
    def angle(self):
        """:term:`ValueLike`: Angle of the bend."""
        return self.prim_obj.GetAngle()

    @angle.setter
    def angle(self, val):
        self.prim_obj.SetAngle(val)

    @property
    def bent_regions(self):
        """:obj:`list` of :class:`PolygonData <ansys.edb.geometry.PolygonData>`: Bent region polygons.

            Collection of polygon data representing the areas bent by this bend definition.

        Read-Only.
        """
        return self.prim_obj.GetBentRegions()
