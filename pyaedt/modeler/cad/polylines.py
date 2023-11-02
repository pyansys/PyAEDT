from __future__ import absolute_import

import math
import warnings

from pyaedt import pyaedt_function_handler
from pyaedt.application.Variables import decompose_variable_value
from pyaedt.generic.constants import PLANE, unit_converter
from pyaedt.generic.general_methods import _dim_arg
from pyaedt.modeler.cad.object3d import Object3d
from pyaedt.modeler.geometry_operators import GeometryOperators


class PolylineSegment(object):
    """Creates and manipulates a segment of a polyline.

    Parameters
    ----------
    segment_type : str
        Type of the object. Choices are ``"Line"``, ``"Arc"``, ``"Spline"``,
        and ``"AngularArc"``.
    num_seg : int, optional
        Number of segments for the types ``"Arc"``, ``"Spline"``, and
        ``"AngularArc"``.  The default is ``0``. For the type
        ``Line``, this parameter is ignored.
    num_points : int, optional
        Number of control points for the type ``Spline``. For other
        types, this parameter is defined automatically.
    arc_angle : float or str, optional
        Sweep angle in radians or a valid value string. For example,
        ``"35deg"`` or ``0.25``.
        This argument is Specific to type AngularArc.
    arc_center : list or str, optional
        List of values in model units or a valid value string. For
        example, a list of ``[x, y, z]`` coordinates.
        This argument is Specific to type AngularArc.
    arc_plane : str, int optional
        Plane in which the arc sweep is performed in the active
        coordinate system ``"XY"``, ``"YZ"`` or ``"ZX"``. The default is
        ``None``, in which case the plane is determined automatically
        by the first coordinate for which the starting point and
        center point have the same value.
        This argument is Specific to type AngularArc.

    Examples
    --------
    See :class:`pyaedt.Primitives.Polyline`.

    """

    def __init__(self, segment_type, num_seg=0, num_points=0, arc_angle=0, arc_center=None, arc_plane=None):
        valid_types = ["Line", "Arc", "Spline", "AngularArc"]
        if segment_type not in valid_types:
            raise TypeError("Segment type must be one of {}.".format(valid_types))
        self.type = segment_type
        if segment_type != "Line":
            self.num_seg = num_seg
        if segment_type == "Line":
            self.num_points = 2
        if segment_type == "Spline":
            self.num_points = num_points
        if "Arc" in segment_type:
            self.num_points = 3
        if segment_type == "AngularArc":
            self.arc_angle = arc_angle
            if not arc_center:
                arc_center = [0, 0, 0]
            if len(arc_center) != 3:
                raise ValueError("Arc center must be a list of length 3.")
            self.arc_center = arc_center
        if isinstance(arc_plane, int):
            if arc_plane == PLANE.XY:
                self.arc_plane = "XY"
            elif arc_plane == PLANE.ZX:
                self.arc_plane = "ZX"
            elif arc_plane == PLANE.YZ:
                self.arc_plane = "YZ"
            else:
                raise ValueError("arc_plane must be 0, 1, or 2 ")
        elif arc_plane:
            if arc_plane not in ["XY", "ZX", "YZ"]:
                raise ValueError('arc_plane must be "XY", "ZX", or "YZ" ')
            self.arc_plane = arc_plane
        else:
            self.arc_plane = None
        self.extra_points = None


class Polyline(Object3d):
    """Creates and manipulates a polyline.

    The constructor for this class is intended to be called from the
    :func:`pyaedt.modeler.Primitives.Primitives.create_polyline` method.
    The documentation is provided there.

    The returned Polyline object exposes the methods for manipulating the polyline.

    Parameters
    ----------
    primitives : :class:`pyaedt.modeler.Primitives3D.Primitives3D`
        Pointer to the parent Primitives object.
    src_object : optional
        The default is ``None``. If specified, all other arguments are ignored.
    position_list : list, optional
        List of positions in the ``[x, y, z]`` format. The default is ``None``.
        It is mandatory if ``scr_object`` is not specified.
    segment_type : str or PolylineSegment or list, optional
        Define the list of segment types.
        For a string, ``"Line"`` or ``"Arc"`` is valid.
        Use a ``"PolylineSegment"``, for ``"Line"``, ``"Arc"``, ``"Spline"``,
        or ``"AngularArc"``.
        A list of segment types (str or :class:`pyaedt.modeler.Primitives.PolylineSegment`) is
        valid for a compound polyline.
        The default is ``None``.
    cover_surface : bool, optional
        The default is ``False``.
    close_surface : bool, optional
        The default is ``False``.
    name : str, optional
        The default is ``None``.
    matname : str, optional
        Name of the material. The default is ``None``.
    xsection_type : str, optional
        Type of the cross-section. Options are ``"Line"``, ``"Circle"``, ``"Rectangle"``,
        and ``"Isosceles Trapezoid"``. The default is ``None``.
    xsection_orient : str, optional
        Direction of the normal vector to the width of the cross-section.
        Options are ``"X"``, ``"Y"``, ``"Z"``, and ``"Auto"``. The
        default is ``None``.
    xsection_width : float or str, optional
        Width or diameter of the cross-section for all types. The default is
        ``1``.
    xsection_topwidth : float or str, optional
        Top width of the cross-section for the type ``"Isosceles Trapezoid"`` only.
        The default is ``1``.
    xsection_height : float or str, optional
        Height of the cross-section for the types ``"Rectangle"`` and ``"Isosceles
        Trapezoid"`` only. The default is ``1``.
    xsection_num_seg : int, optional
        Number of segments in the cross-section surface for the types ``"Circle"``,
        ``"Rectangle"`` and ``"Isosceles Trapezoid"``. The default is ``0``.
        The value must be ``0`` or greater than ``2``.
    xsection_bend_type : str, optional
        Type of the bend. The default is ``None``, in which case the bend type
        is set to ``"Corner"``. For the type ``"Circle"``, the bend type
        should be set to ``"Curved"``.

    """

    def __init__(
        self,
        primitives,
        src_object=None,
        position_list=None,
        segment_type=None,
        cover_surface=False,
        close_surface=False,
        name=None,
        matname=None,
        xsection_type=None,
        xsection_orient=None,
        xsection_width=1,
        xsection_topwidth=1,
        xsection_height=1,
        xsection_num_seg=0,
        xsection_bend_type=None,
        non_model=False,
    ):
        self._primitives = primitives
        self._positions = []
        self._segment_types = []

        if src_object:
            # scr_obj keys need to be added.
            for k in src_object.__dict__:
                self.__dict__[k] = src_object.__dict__[k]

            if name:
                self._m_name = name
            else:
                self._id = src_object.id
                self._m_name = src_object.name
        else:
            self._xsection = self._primitives._crosssection_arguments(
                type=xsection_type,
                orient=xsection_orient,
                width=xsection_width,
                topwidth=xsection_topwidth,
                height=xsection_height,
                num_seg=xsection_num_seg,
                bend_type=xsection_bend_type,
            )

            # validates and create the self._segment_type property and the self._positions property
            if not position_list:
                raise ValueError("The position_list argument must be a list of positions with at least one point.")
            if not isinstance(position_list, list):
                raise TypeError("The position_list argument must be a list of positions with at least one point.")
            # convert the points if they are defined as modeler.Position
            if isinstance(position_list[0], self._primitives._app.modeler.Position):
                position_list = [[i for i in j] for j in position_list]
            if not segment_type:
                if len(position_list) < 2:
                    raise ValueError(
                        "The position_list argument must contain at least 2 points if segment_type is not specified."
                    )
                # add the segment
                self._segment_types = [PolylineSegment("Line")] * (len(position_list) - 1)
                # add the points
                self._positions = [list(i) for i in position_list]
            elif isinstance(segment_type, str):
                if segment_type not in ["Line", "Arc", "Spline"]:
                    raise TypeError('segment must be either "Line", "Arc", "Spline" or PolylineSegment object')
                # add the segment
                self._segment_types = [PolylineSegment(segment_type)]
                # add the points (discard the points in excess)
                if self._segment_types[0].type == "Line":
                    if len(position_list) < 2:
                        raise ValueError(
                            "The position_list argument must contain at least 2 points for segment of type Line."
                        )
                    self._positions = [list(i) for i in position_list[:2]]
                elif self._segment_types[0].type == "Arc":
                    if len(position_list) < 3:
                        raise ValueError(
                            "The position_list argument must contain at least 3 points for segment of type Arc."
                        )
                    self._positions = [list(i) for i in position_list[:3]]
                elif self._segment_types[0].type == "Spline":
                    if len(position_list) < 4:
                        raise ValueError(
                            "The position_list argument must contain at least 4 points for segment of type Spline."
                        )
                    self._positions = [list(i) for i in position_list[::]]
                    self._segment_types[0].num_points = len(position_list)
            elif isinstance(segment_type, PolylineSegment):
                # add the segment
                self._segment_types = [segment_type]
                # add the points
                if segment_type.type == "Line":
                    if len(position_list) < 2:
                        raise ValueError(
                            "The position_list argument must contain at least 2 points for segment of type Line."
                        )
                    self._positions = [list(i) for i in position_list[:2]]
                elif segment_type.type == "Arc":
                    if len(position_list) < 3:
                        raise ValueError(
                            "The position_list argument must contain at least 3 points for segment of type Arc."
                        )
                    self._positions = [list(i) for i in position_list[:3]]
                elif segment_type.type == "Spline":
                    if len(position_list) < self._segment_types[-1].num_points:
                        raise ValueError(
                            "The position_list argument must contain all points required by the segment of type Spline."
                        )
                    self._positions = [list(i) for i in position_list[: self._segment_types[-1].num_points]]
                else:  # AngularArc
                    self._positions = [position_list[0]]
                    self._evaluate_arc_angle_extra_points(segment_type, start_point=position_list[0])
                    self._positions.extend(segment_type.extra_points[:])
            elif isinstance(segment_type, list):
                i_pos = 0
                for i, seg in enumerate(segment_type):
                    # add the segments
                    if isinstance(seg, str):
                        if seg not in ["Line", "Arc", "Spline"]:
                            raise TypeError('segment must be either "Line", "Arc", "Spline" or PolylineSegment object')
                        # Convert all string-type entries in the segment_types list to PolylineSegments
                        self._segment_types.append(PolylineSegment(seg))
                    elif isinstance(seg, PolylineSegment):
                        self._segment_types.append(seg)
                    else:
                        raise TypeError("Invalid segment_type input of type {}".format(type(seg)))
                    # add the points
                    if i == 0:  # append the first point only for the first segment
                        self._positions.append(list(position_list[0]))
                    # add the other points
                    if self._segment_types[-1].type == "Line":
                        if len(position_list[i_pos : i_pos + 2]) < 2:
                            raise ValueError(
                                "The position_list argument must contain at least 2 points for segment of type Line."
                            )
                        self._positions.extend([list(i) for i in position_list[i_pos + 1 : i_pos + 2]])
                        i_pos += 1
                    elif self._segment_types[-1].type == "Arc":
                        if (not close_surface and len(position_list[i_pos : i_pos + 3]) < 3) or (
                            close_surface and len(position_list[i_pos : i_pos + 3]) < 2
                        ):
                            raise ValueError(
                                "The position_list argument must contain at least 3 points for segment of type Arc."
                            )
                        self._positions.extend([list(i) for i in position_list[i_pos + 1 : i_pos + 3]])
                        i_pos += 2
                    elif self._segment_types[-1].type == "Spline":
                        nsp = self._segment_types[-1].num_points
                        if len(position_list[i_pos : i_pos + nsp]) < nsp:
                            raise ValueError(
                                "The position_list argument must contain all points required by the segment Spline."
                            )
                        self._positions.extend([list(i) for i in position_list[: self._segment_types[-1].num_points]])
                        i_pos += nsp - 1
                    else:  # AngularArc
                        start = position_list[i_pos]
                        self._evaluate_arc_angle_extra_points(self._segment_types[-1], start_point=start)
                        self._positions.extend(self._segment_types[-1].extra_points[:])
            else:
                raise TypeError("Invalid segment_type input of type {}".format(type(segment_type)))

            # When close surface or cover_surface are set to True, ensure the start point and end point are coincident,
            # and insert a line segment to achieve this if necessary
            if cover_surface:
                close_surface = True

            self._is_closed = close_surface
            self._is_covered = cover_surface

            varg1 = self._point_segment_string_array()
            if non_model:
                flag = "NonModel#"
            else:
                flag = ""
            varg2 = self._primitives._default_object_attributes(name=name, matname=matname, flags=flag)

            new_object_name = self._oeditor.CreatePolyline(varg1, varg2)
            Object3d.__init__(self, primitives, name=new_object_name)
            self._primitives._create_object(self.name)

    @property
    def start_point(self):
        """List of the ``[x, y, z]`` coordinates for the starting point in the polyline
        object in the object's coordinate system.

        Returns
        -------
        list
            List of the ``[x, y, z]`` coordinates for the starting point in the polyline
            object.

        """
        return self.points[0]

    @property
    def end_point(self):
        """List of the ``[x, y, z]`` coordinates for the ending point in the polyline
        object in the object's coordinate system.

        Returns
        -------
        list
            List of the ``[x, y, z]`` coordinates for the ending point in the polyline
            object.

        References
        ----------
        >>> oEditor.GetVertexIDsFromObject
        >>> oEditor.GetVertexPosition

        """
        return self.points[-1]

    def _update_segments_and_points(self):
        """Updates the self._segment_types and the self._positions from the history.
        This internal method is called by properties ``points`` and ``segment_types``.
        It will be called only once after opening a new project, then the internal
        variables are maintained updated.
        It is a single update call for both properties because they are very similar,
        and we can access to the history only once.
        """

        def _convert_points(p_in, dest_unit):
            p_out = []
            for ip in p_in:
                v, u = decompose_variable_value(ip)
                if u == "":
                    p_out.append(v)
                else:
                    p_out.append(unit_converter(v, unit_system="Length", input_units=u, output_units=dest_unit))
            return p_out

        segments = []
        points = []
        try:
            history = self.history()
            h_segments = history.segments
        except:  # pragma: no cover
            history = None
            h_segments = None
        if h_segments:
            for i, c in enumerate(h_segments.values()):
                # evaluate the number of points in the segment
                attrb = list(c.props.keys())
                n_points = 0
                for j in range(1, len(attrb) + 1):
                    if "Point" + str(j) in attrb:
                        n_points += 1
                # get the segment type
                s_type = c.props["Segment Type"]
                if i == 0:  # append the first point only for the first segment
                    if s_type != "Center Point Arc":
                        points.append(_convert_points(list(c.props["Point1"])[1::2], self._primitives.model_units))
                    else:
                        points.append(_convert_points(list(c.props["Start Point"])[1::2], self._primitives.model_units))
                if s_type == "Line":
                    segments.append(PolylineSegment("Line"))
                    points.append(_convert_points(list(c.props["Point2"])[1::2], self._primitives.model_units))
                elif s_type == "3 Point Arc":
                    segments.append(PolylineSegment("Arc"))
                    points.append(_convert_points(list(c.props["Point2"])[1::2], self._primitives.model_units))
                    points.append(_convert_points(list(c.props["Point3"])[1::2], self._primitives.model_units))
                elif s_type == "Spline":
                    segments.append(PolylineSegment("Spline", num_points=n_points))
                    for p in range(2, n_points + 1):
                        point_attr = c.props["Point" + str(p)]
                        points.append(_convert_points(list(point_attr)[1::2], self._primitives.model_units))
                elif s_type == "Center Point Arc":
                    start = _convert_points(list(c.props["Start Point"])[1::2], self._primitives.model_units)
                    center = _convert_points(list(c.props["Center Point"])[1::2], self._primitives.model_units)
                    plane = c.props["Plane"]
                    angle = c.props["Angle"]
                    arc_seg = PolylineSegment("AngularArc", arc_angle=angle, arc_center=center, arc_plane=plane)
                    segments.append(arc_seg)
                    self._evaluate_arc_angle_extra_points(arc_seg, start)
                    points.extend(arc_seg.extra_points[:])

        # perform validation
        if history:
            nn_segments = int(history.props["Number of curves"])
            nn_points = int(history.props["Number of points"])
        else:
            nn_segments = None
            nn_points = None
        assert len(segments) == nn_segments, "Error getting the polyline segments from AEDT."
        assert len(points) == nn_points, "Error getting the polyline points from AEDT."
        # if succeeded save the result
        self._segment_types = segments
        self._positions = points

    @property
    def points(self):
        """Polyline Points."""
        if self._positions:
            return self._positions
        else:
            self._update_segments_and_points()
            return self._positions

    @property
    def segment_types(self):
        """List of the segment types of the polyline."""
        if self._segment_types:
            return self._segment_types
        else:
            self._update_segments_and_points()
            return self._segment_types

    @property
    def vertex_positions(self):
        """List of the ``[x, y, z]`` coordinates for all vertex positions in the
        polyline object in the object's coordinate system.

        Returns
        -------
        list
            List of the ``[x, y, z]`` coordinates for all vertex positions in the
            polyline object.

        References
        ----------
        >>> oEditor.GetVertexIDsFromObject
        >>> oEditor.GetVertexPosition

        """
        id_list = self._primitives.get_object_vertices(partID=self.id)
        position_list = [self._primitives.get_vertex_position(id) for id in id_list]
        return position_list

    @pyaedt_function_handler()
    def _pl_point(self, pt):
        pt_data = ["NAME:PLPoint"]
        pt_data.append("X:=")
        pt_data.append(_dim_arg(pt[0], self._primitives.model_units))
        pt_data.append("Y:=")
        pt_data.append(_dim_arg(pt[1], self._primitives.model_units))
        pt_data.append("Z:=")
        pt_data.append(_dim_arg(pt[2], self._primitives.model_units))
        return pt_data

    @pyaedt_function_handler()
    def _point_segment_string_array(self):
        """Retrieve the parameter arrays for specifying the points and segments of a polyline
        used in the :class:`pyaedt.modeler.Primitives.Polyline` constructor.

        Returns
        -------
        list

        """
        position_list = self.points
        segment_types = self.segment_types

        # Add a closing point if needed
        varg1 = ["NAME:PolylineParameters"]
        varg1.append("IsPolylineCovered:=")
        varg1.append(self._is_covered)
        varg1.append("IsPolylineClosed:=")
        varg1.append(self._is_closed)

        # PointsArray
        points_str = ["NAME:PolylinePoints"]
        points_str.append(self._pl_point(position_list[0]))

        # Segments Array
        segment_str = ["NAME:PolylineSegments"]

        pos_count = 0
        vertex_count = 0
        index_count = 0

        while vertex_count <= len(segment_types):
            try:
                current_segment = None
                if vertex_count == len(segment_types):
                    if self._is_closed:
                        # Check the special case of a closed polyline needing an additional Line segment
                        if position_list[0] != position_list[-1]:
                            position_list.append(position_list[0])
                            current_segment = PolylineSegment("Line")
                    else:
                        break
                else:
                    current_segment = segment_types[vertex_count]
            except Exception:
                raise IndexError("Number of segments inconsistent with the number of points!")

            if current_segment:
                seg_str = self._segment_array(
                    current_segment, start_index=index_count, start_point=position_list[pos_count]
                )
                segment_str.append(seg_str)

                pos_count_incr = 0
                for i in range(1, current_segment.num_points):
                    if current_segment.type == "AngularArc":
                        points_str.append(self._pl_point(current_segment.extra_points[i - 1]))
                        index_count += 1
                    else:
                        if (pos_count + i) == len(position_list):
                            if current_segment.type == "Arc" and self._is_closed:
                                position_list.append(position_list[0])
                            else:
                                err_str = "Insufficient points in position_list to complete the specified segment list"
                                raise ValueError(err_str)
                        points_str.append(self._pl_point(position_list[pos_count + i]))
                        pos_count_incr += 1
                        index_count += 1
                pos_count += pos_count_incr
                vertex_count += 1
            else:
                break

        varg1.append(points_str)
        varg1.append(segment_str)

        # Poly Line Cross Section
        varg1.append(self._xsection)

        return varg1

    @pyaedt_function_handler()
    def _evaluate_arc_angle_extra_points(self, segment, start_point):
        """Evaluate the extra points for the ArcAngle segment type.
        It also auto evaluates the arc_plane if it was not specified by the user.
        segment.extra_points[0] contains the arc mid point (on the arc).
        segment.extra_points[1] contains the arc end point.
        Both are function of the arc center, arc angle and arc plane.
        """
        # from start-point and angle, calculate the mid-point and end-points
        # Also identify the plane of the arc ("YZ", "ZX", "XY")
        plane_axes = {"YZ": [1, 2], "ZX": [2, 0], "XY": [0, 1]}
        c_xyz = self._primitives.value_in_object_units(segment.arc_center)
        p0_xyz = self._primitives.value_in_object_units(start_point)

        if segment.arc_plane:
            # Accept the user input for the plane of rotation - let the modeler fail if invalid
            plane_def = (segment.arc_plane, plane_axes[segment.arc_plane])
        else:
            # Compare the numeric values of start-point and center-point to determine the orientation plane
            if c_xyz[0] == p0_xyz[0]:
                plane_def = ("YZ", plane_axes["YZ"])
            elif c_xyz[1] == p0_xyz[1]:
                plane_def = ("ZX", plane_axes["ZX"])
            elif c_xyz[2] == p0_xyz[2]:
                plane_def = ("XY", plane_axes["XY"])
            else:
                raise Exception("Start point and arc-center do not lie on a common base plane.")
            segment.arc_plane = plane_def[0]

        # Calculate the extra two points of the angular arc in the alpha-beta plane
        alph_index = plane_def[1][0]
        beta_index = plane_def[1][1]
        c_alph = c_xyz[alph_index]
        c_beta = c_xyz[beta_index]
        p0_alph = p0_xyz[alph_index] - c_alph
        p0_beta = p0_xyz[beta_index] - c_beta

        # rotate to generate the new points
        arc_ang = self._primitives._app.evaluate_expression(segment.arc_angle)  # in radians
        h_arc_ang = arc_ang * 0.5

        p1_alph = c_alph + p0_alph * math.cos(h_arc_ang) - p0_beta * math.sin(h_arc_ang)
        p1_beta = c_beta + p0_alph * math.sin(h_arc_ang) + p0_beta * math.cos(h_arc_ang)
        p2_alph = c_alph + p0_alph * math.cos(arc_ang) - p0_beta * math.sin(arc_ang)
        p2_beta = c_beta + p0_alph * math.sin(arc_ang) + p0_beta * math.cos(arc_ang)

        # Generate the 2 new points in XYZ
        p1 = list(p0_xyz)
        p1[alph_index] = p1_alph
        p1[beta_index] = p1_beta
        p2 = list(p0_xyz)
        p2[alph_index] = p2_alph
        p2[beta_index] = p2_beta
        segment.extra_points = [p1, p2]
        return True

    @pyaedt_function_handler()
    def _segment_array(self, segment_data, start_index=0, start_point=None):
        """Retrieve a property array for a polyline segment for use in the
        :class:`pyaedt.modeler.Primitives.Polyline` constructor.

        Parameters
        ----------
        segment_data : :class:`pyaedt.modeler.Primitives.PolylineSegment` or str
            Pointer to the calling object that provides additional functionality
            or a string with the segment type ``Line`` or ``Arc``.
        start_index : int, string
            Starting vertex index of the segment within a compound polyline. The
            default is ``0``.
        start_point : list, optional
            Position of the first point for type ``AngularArc``. The default is
            ``None``. Float values are considered in model units.

        Returns
        -------
        list
            List of properties defining a polyline segment.

        """
        if isinstance(segment_data, str):
            segment_data = PolylineSegment(segment_data)

        seg = [
            "NAME:PLSegment",
            "SegmentType:=",
            segment_data.type,
            "StartIndex:=",
            start_index,
            "NoOfPoints:=",
            segment_data.num_points,
        ]
        if segment_data.type != "Line":
            seg += ["NoOfSegments:=", "{}".format(segment_data.num_seg)]

        if segment_data.type == "AngularArc":
            # from start-point and angle, calculate the mid- and end-points
            assert start_point, "Start-point must be defined for an AngularArc Segment"
            self._evaluate_arc_angle_extra_points(segment_data, start_point)

            mod_units = self._primitives.model_units
            seg += [
                "ArcAngle:=",
                segment_data.arc_angle,
                "ArcCenterX:=",
                "{}".format(_dim_arg(segment_data.arc_center[0], mod_units)),
                "ArcCenterY:=",
                "{}".format(_dim_arg(segment_data.arc_center[1], mod_units)),
                "ArcCenterZ:=",
                "{}".format(_dim_arg(segment_data.arc_center[2], mod_units)),
                "ArcPlane:=",
                segment_data.arc_plane,
            ]

        return seg

    @pyaedt_function_handler()
    def clone(self):
        """Clone a polyline object.

        Returns
        -------
        pyaedt.modeler.polylines.Polyline
            Polyline object that was created.

        References
        ----------
        >>> oEditor.Copy
        >>> oEditor.Paste

        Examples
        --------
        >>> primitives = self.aedtapp.modeler
        >>> P1 = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        >>> P2 = P1.clone()

        """
        vArg1 = ["NAME:Selections", "Selections:=", self.name]
        self._primitives.oeditor.Copy(vArg1)
        self._primitives.oeditor.Paste()
        return self._add_new_polyline()

    @pyaedt_function_handler()
    def _add_new_polyline(self):
        new_objects = self._primitives.find_new_objects()
        assert len(new_objects) == 1
        new_name = new_objects[0]
        new_polyline = Polyline(self._primitives, src_object=self, name=new_name)
        new_polyline._id = None
        return self._primitives._create_object(new_name)

    @pyaedt_function_handler()
    def remove_vertex(self, position, abstol=1e-9):
        """Remove a vertex from an existing polyline by position.

        .. deprecated:: 0.6.55
           Use :func:``remove_point`` method instead.

        """
        warnings.warn("`remove_vertex` is deprecated. Use `remove_point` method instead.", DeprecationWarning)
        return self.remove_point(position, abstol)

    @pyaedt_function_handler()
    def remove_point(self, position, abstol=1e-9):
        """Remove a point from an existing polyline by position.

        You must enter the exact position of the vertex as a list
        of ``[x, y, z]`` coordinates in the object's coordinate system.

        Parameters
        ----------
        position : list
            List of ``[x, y, z]`` coordinates specifying the vertex to remove.
        abstol : float, optional
            Absolute tolerance of the comparison of a specified position to the
            vertex positions. The default is ``1e-9``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.DeletePolylinePoint

        Examples
        --------
        Use floating point values for the vertex positions.

        >>> P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        >>> P.remove_point([0, 1, 2])

        Use string expressions for the vertex position.

        >>> P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        >>> P.remove_point(["0mm", "1mm", "2mm"])

        Use string expressions for the vertex position and include an absolute
        tolerance when searching for the vertex to be removed.

        >>> P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        >>> P.remove_point(["0mm", "1mm", "2mm"], abstol=1e-6)
        """
        found_vertex = False
        seg_id = None
        at_start = None
        pos_xyz = self._primitives.value_in_object_units(position)
        for ind, point_pos in enumerate(self.points):
            # compare the specified point with the vertex data using an absolute tolerance
            # (default of math.isclose is 1e-9 which should be ok in almost all cases)
            found_vertex = GeometryOperators.points_distance(point_pos, pos_xyz) <= abstol
            if found_vertex:
                if ind == len(self.points) - 1:
                    at_start = False
                    seg_id = self._get_segment_id_from_point_n(ind, at_start, allow_inner_points=True)
                else:
                    at_start = True
                    seg_id = self._get_segment_id_from_point_n(ind, at_start, allow_inner_points=True)
                break

        if not found_vertex or seg_id is None or at_start is None:
            raise ValueError("Specified vertex {} not found in polyline {}.".format(position, self._m_name))

        try:
            self._primitives.oeditor.DeletePolylinePoint(
                [
                    "NAME:Delete Point",
                    "Selections:=",
                    self._m_name + ":CreatePolyline:1",
                    "Segment Indices:=",
                    [seg_id],
                    "At Start:=",
                    at_start,
                ]
            )
        except:  # pragma: no cover
            raise ValueError("Invalid edge ID {} is specified on polyline {}.".format(seg_id, self.name))
        else:
            i_start, i_end = self._get_point_slice_from_segment_id(seg_id, at_start)
            del self._positions[i_start:i_end]
            del self._segment_types[seg_id]

        return True

    @pyaedt_function_handler()
    def remove_edges(self, edge_id):
        """Remove a segment from an existing polyline by segment id.

        .. deprecated:: 0.6.55
           Use :func:``remove_segments`` method instead.

        """
        warnings.warn("`remove_edges` is deprecated. Use `remove_segments` method instead.", DeprecationWarning)
        return self.remove_segments(segment_id=edge_id)

    @pyaedt_function_handler()
    def remove_segments(self, segment_id):
        """Remove a segment from an existing polyline by segment id.

        You must enter the segment id or the list of the segment ids you want to remove.

        Parameters
        ----------
        segment_id : int or List of int
            One or more edge IDs within the total number of edges of the polyline.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.DeletePolylinePoint

        Examples
        --------
        >>> P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        >>> P.remove_segments(segment_id=0)
        """
        if isinstance(segment_id, int):
            segment_id = [segment_id]
        elif isinstance(segment_id, list):
            segment_id.sort()
        else:
            raise TypeError("segment_id must be int or list of int.")
        try:
            self._primitives.oeditor.DeletePolylinePoint(
                [
                    "NAME:Delete Point",
                    "Selections:=",
                    self.name + ":CreatePolyline:1",
                    "Segment Indices:=",
                    segment_id,
                    "At Start:=",
                    True,
                ]
            )
        except:  # pragma: no cover
            raise ValueError("Invalid segment ID {} is specified on polyline {}.".format(segment_id, self.name))
        else:
            segment_id.reverse()
            for sid in segment_id:
                if sid == len(self._segment_types) - 1:
                    # removing the last segment, AEDT removes ALWAYS the last polyline point
                    at_start = False
                else:
                    at_start = True
                i_start, i_end = self._get_point_slice_from_segment_id(sid, at_start)
                del self._positions[i_start:i_end]
                del self._segment_types[sid]
        return True

    @pyaedt_function_handler()
    def set_crosssection_properties(
        self, type=None, orient=None, width=0, topwidth=0, height=0, num_seg=0, bend_type=None
    ):
        """Set the properties of an existing polyline object.

        Parameters
        ----------
        type : str, optional
            Types of the cross-sections. Options are ``"Line"``, ``"Circle"``, ``"Rectangle"``,
            and ``"Isosceles Trapezoid"``. The default is ``None``.
        orient : str, optional
            Direction of the normal vector to the width of the cross-section.
            Options are ``"X"``, ``"Y"``, ``"Z"``, and ``"Auto"``. The default
            is ``None``, which sets the orientation to ``"Auto"``.
        width : float or str, optional
           Width or diameter of the cross-section for all types. The default is
           ``0``.
        topwidth : float or str
           Top width of the cross-section for the type ``"Isosceles Trapezoid"``
           only. The default is ``0``.
        height : float or str
            Height of the cross-section for the types ``"Rectangle"`` and `"Isosceles
            Trapezoid"`` only. The default is ``0``.
        num_seg : int, optional
            Number of segments in the cross-section surface for the types ``"Circle"``,
            ``"Rectangle"``, and ``"Isosceles Trapezoid"``. The default is ``0``.
            The value must be ``0`` or greater than ``2``.
        bend_type : str, optional
            Type of the bend. The default is ``None``, in which case the bend type
            is set to ``"Corner"``. For the type ``"Circle"``, the bend type should be
            set to ``"Curved"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty

        Examples
        --------
        >>> P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        >>> P.set_crosssection_properties(type="Circle", width="1mm")

        """
        # Set the default section type to "None"
        section_type = type
        if not section_type:
            section_type = "None"

        # Set the default orientation to "Auto"
        section_orient = orient
        if not section_orient:
            section_orient = "Auto"

        # Set the default bend-type to "Corner"
        section_bend = bend_type
        if not section_bend:
            section_bend = "Corner"

        # Ensure number-of segments is valid
        if num_seg:
            assert num_seg > 2, "Number of segments for a cross-section must be 0 or greater than 2."

        model_units = self._primitives.model_units

        arg1 = ["NAME:AllTabs"]
        arg2 = ["NAME:Geometry3DCmdTab", ["NAME:PropServers", self._m_name + ":CreatePolyline:1"]]
        arg3 = ["NAME:ChangedProps"]
        arg3.append(["NAME:Type", "Value:=", section_type])
        arg3.append(["NAME:Orientation", "Value:=", section_orient])
        arg3.append(["NAME:Bend Type", "Value:=", section_bend])
        arg3.append(["NAME:Width/Diameter", "Value:=", _dim_arg(width, model_units)])
        if section_type == "Rectangle":
            arg3.append(["NAME:Height", "Value:=", _dim_arg(height, model_units)])
        elif section_type == "Circle":
            arg3.append(["NAME:Number of Segments", "Value:=", num_seg])
        elif section_type == "Isosceles Trapezoid":
            arg3.append(["NAME:Top Width", "Value:=", _dim_arg(topwidth, model_units)])
            arg3.append(["NAME:Height", "Value:=", _dim_arg(height, model_units)])
        arg2.append(arg3)
        arg1.append(arg2)
        self._primitives.oeditor.ChangeProperty(arg1)
        return self._primitives.update_object(self.name)

    @pyaedt_function_handler()
    def _get_point_slice_from_segment_id(self, segment_id, at_start=True):
        """Get the points belonging to the segment from the segment id.
        The points are returned as list slice by returning the indexes.

        Parameters
        ----------
        segment_id : int
            segment id

        at_start : bool
            if ``True`` the slice includes the start point of the segment and not the end point.
            If ``False`` the slice includes the end point of the segment and not the start point.

        Returns
        -------
        tuple of int, bool
            Indexes of the list slice. ``False`` when failed.
        """
        i_end = 0
        for i, s in enumerate(self.segment_types):
            i_start = i_end
            if s.type == "Line":
                i_end += 1
            elif s.type == "Arc":
                i_end += 2
            elif s.type == "AngularArc":
                i_end += 2
            elif s.type == "Spline":
                i_end += s.num_points - 1
            if i == segment_id:
                if at_start:
                    return i_start, i_end
                else:
                    return i_start + 1, i_end + 1
        return False

    @pyaedt_function_handler()
    def _get_segment_id_from_point_n(self, pn, at_start, allow_inner_points=False):
        """Get the segment id for a given point index considering the segment types in the polyline.
        If a segment cannot be found with the specified rules, the function returns False.

        Parameters
        ----------
        pn : int
            point number along the polyline
        at_start : bool
            If set to ``True`` the segment id that begins with the point pn is returned.
            If set to ``False`` the segment id that terminates with the point pn is returned.
        allow_inner_points : bool, optional
            If set to ``False`` only points that are at the extremities of the segments are considered.
            If pn is in the middle of a segment, the function returns False.
            If set to ``True`` also points in the middle of the segments are considered.

        Returns
        -------
        int, bool
            Segment id when successful. ``False`` when failed.
        """
        n_points = 0
        for i, s in enumerate(self.segment_types):
            if n_points == pn and at_start:
                return i
            n_points_imu = n_points
            if s.type == "Line":
                n_points += 1
            elif s.type == "Arc":
                n_points += 2
            elif s.type == "AngularArc":
                n_points += 2
            elif s.type == "Spline":
                n_points += s.num_points - 1
            if n_points == pn and not at_start:
                return i
            if n_points_imu < pn < n_points and allow_inner_points:
                return i
        return False

    @pyaedt_function_handler()
    def insert_segment(self, position_list, segment=None):
        """Add a segment to an existing polyline.

        Parameters
        ----------
        position_list : List
            List of positions of the points that define the segment to insert.
            Either the starting point or ending point of the segment list must
            match one of the vertices of the existing polyline.
        segment : str or :class:`pyaedt.modeler.Primitives.PolylineSegment`, optional
            Definition of the segment to insert. For the types ``"Line"`` and ``"Arc"``,
            use their string values ``"Line"`` and ``"Arc"``. For the types ``"AngularArc"``
            and ``"Spline"``, use the :class:`pyaedt.modeler.Primitives.PolylineSegment`
            object to define the segment precisely. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.InsertPolylineSegment

        """
        # Check for a valid number of points
        num_points = len(position_list)

        # define the segment type from the number of points given
        if not segment:
            if num_points < 2:
                raise ValueError("num_points must contain at least 2 points to auto-define a segment.")
            if num_points == 2:
                segment = PolylineSegment("Line")
            elif num_points == 3:
                segment = PolylineSegment("Arc")
            else:  # num_points>3
                segment = PolylineSegment("Spline", num_points=num_points)
        else:
            if isinstance(segment, str) and segment in ["Line", "Arc"]:
                segment = PolylineSegment(segment)
                num_points = segment.num_points
            elif isinstance(segment, PolylineSegment):
                num_points = segment.num_points
                if segment.type == "AngularArc":
                    self._evaluate_arc_angle_extra_points(segment, start_point=position_list[0])
            else:
                raise TypeError('segment must be either "Line", "Arc" or PolylineSegment object.')
            if segment.type != "AngularArc" and len(position_list) < num_points:
                raise ValueError("position_list must contain enough points for the specified segment type.")
            elif segment.type == "AngularArc" and len(position_list) < 1:
                raise ValueError("position_list must contain the start point for AngularArc segment.")

        # Check whether start-point and end-point of the segment is in the existing polylines points
        start_point = position_list[0]

        # End point does not exist for an AngularArc
        if segment.type != "AngularArc":
            end_point = position_list[-1]
        else:
            end_point = []

        at_start = None
        p_insert_position = None
        insert_points = None
        num_polyline_points = len(self.points)
        i = None
        for i, point in enumerate(self.points):
            if end_point and (
                GeometryOperators.points_distance(
                    self._primitives.value_in_object_units(point), self._primitives.value_in_object_units(end_point)
                )
                < 1e-8
            ):
                at_start = True
                p_insert_position = i
                insert_points = position_list[: num_points - 1]  # All points but last one.
                if i == num_polyline_points - 1:
                    if segment.type != "Line":
                        # Inserting a segment in this position is not allowed in AEDT.
                        # We can make it work only for "Line" segments.
                        return False
                    at_start = False
                    position_list = [self.points[-2], start_point]
                break
            elif (
                GeometryOperators.points_distance(
                    self._primitives.value_in_object_units(point), self._primitives.value_in_object_units(start_point)
                )
                < 1e-8
            ):
                # note that AngularArc can only be here
                at_start = False
                p_insert_position = i + 1
                if segment.type != "AngularArc":
                    insert_points = position_list[1:num_points]  # Insert all points but first one
                else:
                    insert_points = segment.extra_points[:]  # For AngularArc insert the extra points
                if i == 0:
                    if segment.type != "Line":
                        # Inserting a segment in this position is not allowed in AEDT.
                        # PyAEDT can make it work only for "Line" segments.
                        return False
                    at_start = True
                    position_list = [end_point, self.points[1]]
                break

        assert p_insert_position is not None, "Point for the insert is not found."
        assert insert_points is not None, "Point for the insert is not found."

        if i is None:
            raise ValueError("The polyline contains no points. It is impossible to insert a segment.")
        segment_index = self._get_segment_id_from_point_n(i, at_start=at_start)

        assert isinstance(segment_index, int), "Segment for the insert is not found."
        if at_start:
            s_insert_position = segment_index
        else:
            s_insert_position = segment_index + 1

        type = segment.type

        varg1 = ["NAME:Insert Polyline Segment"]
        varg1.append("Selections:=")
        varg1.append(self._m_name + ":CreatePolyline:1")
        varg1.append("Segment Indices:=")
        varg1.append([segment_index])
        varg1.append("At Start:=")
        varg1.append(at_start)
        varg1.append("SegmentType:=")
        varg1.append(type)

        # Points and segment data
        varg2 = ["NAME:PolylinePoints"]

        if segment.type == "Line" or segment.type == "Spline" or segment.type == "Arc":
            for pt in position_list[0:num_points]:
                varg2.append(self._pl_point(pt))
            varg1.append(varg2)
        elif segment.type == "AngularArc":
            seg_str = self._segment_array(segment, start_point=start_point)
            varg2.append(self._pl_point(start_point))
            varg2.append(self._pl_point(segment.extra_points[0]))
            varg2.append(self._pl_point(segment.extra_points[1]))
            varg1.append(varg2)
            varg1 += seg_str[9:]
        self._primitives.oeditor.InsertPolylineSegment(varg1)

        # check if the polyline has been modified correctly
        if self._check_polyline_health() is False:
            raise ValueError("Adding the segment result in an unclassified object. Undoing operation.")

        # add the points and the segment to the object
        self._positions[p_insert_position:p_insert_position] = insert_points
        self._segment_types[s_insert_position:s_insert_position] = [segment]

        return True

    @pyaedt_function_handler()
    def _check_polyline_health(self):
        # force re-evaluation of object_type
        self._object_type = None
        if self.object_type == "Unclassified":
            # Undo operation
            self._primitives._app.odesign.Undo()
            self._object_type = None
            assert self.object_type != "Unclassified", "Undo operation failed."
            return False
        return True
