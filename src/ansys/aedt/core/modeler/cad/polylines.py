# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 - 2025 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.cad.object_3d import PolylineSegment


class Polyline(Object3d):
    """Creates and manipulates a polyline.

    The constructor for this class is intended to be called from the
    :func:`ansys.aedt.core.modeler.cad.primitives.Primitives.create_polyline` method.
    The documentation is provided there.

    The returned Polyline object exposes the methods for manipulating the polyline.

    Parameters
    ----------
    primitives : :class:`ansys.aedt.core.modeler.cad.primitives_3d.Primitives3D`
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
        A list of segment types (str or :class:`ansys.aedt.core.modeler.cad.primitives.PolylineSegment`) is
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
        self._is_polyline = True
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
            if isinstance(position_list[0], self._primitives.Position):
                position_list = [[j.X, j.Y, j.Z] for j in position_list]
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
                    if not all(isinstance(x, list) for x in position_list):
                        position_list = [position_list]
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
                        raise TypeError(f"Invalid segment_type input of type {type(seg)}")
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
                raise TypeError(f"Invalid segment_type input of type {type(segment_type)}")

            # When close surface or cover_surface are set to True, ensure the start point and end point are coincident,
            # and insert a line segment to achieve this if necessary
            if cover_surface:
                close_surface = True

            self._is_closed = close_surface
            self._is_covered = cover_surface

            arg_1 = self._point_segment_string_array()
            if non_model:
                flag = "NonModel#"
            else:
                flag = ""
            arg_2 = self._primitives._default_object_attributes(name=name, material=matname, flags=flag)
            if self._primitives.design_type in ["Maxwell 2D", "2D Extractor"]:
                solve_inside_idx = arg_2.index("SolveInside:=")
                self._solve_inside = False
                arg_2[solve_inside_idx + 1] = self._solve_inside
            new_object_name = self._oeditor.CreatePolyline(arg_1, arg_2)
            positions = self._positions
            Object3d.__init__(self, primitives, name=new_object_name)
            self._is_polyline = True
            self._positions = positions
            self._primitives._create_object(self.name, is_polyline=True)
