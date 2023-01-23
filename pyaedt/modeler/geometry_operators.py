# -*- coding: utf-8 -*-
import math
import re
import sys

from pyaedt.generic.constants import AXIS
from pyaedt.generic.constants import PLANE
from pyaedt.generic.constants import SWEEPDRAFT
from pyaedt.generic.constants import scale_units
from pyaedt.generic.general_methods import pyaedt_function_handler


class GeometryOperators(object):
    """Manages geometry operators."""

    @staticmethod
    @pyaedt_function_handler()
    def List2list(input_list):
        """Convert a C# list object to a Python list.

        This function performs a deep conversion.

        Parameters
        ----------
        input_list : list
            C# list to convert to a Python list.

        Returns
        -------
        list
            Converted Python list.

        """
        output_list = []
        for i in input_list:
            if "List" in str(type(i)):
                output_list.append(GeometryOperators.List2list(list(i)))
            else:
                output_list.append(i)
        return output_list

    @staticmethod
    @pyaedt_function_handler()
    def parse_dim_arg(string, scale_to_unit=None, variable_manager=None):
        """Convert a number and unit to a float.
        Angles are converted in radians.

        Parameters
        ----------
        string : str
            String to convert. For example, ``"2mm"``.
        scale_to_unit : str
            Units for the value to convert. For example, ``"mm"``.
        variable_manager : :class:`pyaedt.application.Variables.VariableManager`, optional
            Try to parse formula and returns numeric value.

        Returns
        -------
        float
            Value for the converted value and units. For example, ``0.002``.

        Examples
        --------
        Parse `'"2mm"'`.

        >>> from pyaedt.modeler.geometry_operators import GeometryOperators as go
        >>> go.parse_dim_arg('2mm')
        >>> 0.002

        Use the optional argument ``scale_to_unit`` to specify the destination unit.

        >>> go.parse_dim_arg('2mm', scale_to_unit='mm')
        >>> 2.0

        """

        if type(string) is not str:
            try:
                return float(string)
            except ValueError:  # pragma: no cover
                raise TypeError("Input argument is not string nor number")
        sunit = 1.0
        if scale_to_unit:
            sunit = scale_units(scale_to_unit)

        pattern = r"(?P<number>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s*(?P<unit>[a-z_A-Z]*)"
        m = re.search(pattern, string)
        if m:
            if m.group(0) != string:
                if variable_manager:
                    variable_manager["temp_var"] = string
                    value = variable_manager["temp_var"].numeric_value
                    del variable_manager["temp_var"]
                    return value
                else:
                    return string
            elif not m.group("unit"):
                return float(m.group("number"))
            else:
                scaling_factor = scale_units(m.group("unit"))
                return float(m.group("number")) * scaling_factor / sunit
        else:
            if variable_manager:
                if not variable_manager.set_variable("temp_var", string):
                    if not variable_manager.set_variable("temp_var", string, postprocessing=True):
                        return string
                value = variable_manager["temp_var"].value / sunit
                del variable_manager["temp_var"]
                return value

    @staticmethod
    @pyaedt_function_handler()
    def cs_plane_to_axis_str(val):
        """Retrieve a string for a coordinate system plane.

        Parameters
        ----------
        val :


        Returns
        -------
        str
           String for the coordinate system plane.

        """
        if val == PLANE.XY or val == "XY":
            return "Z"
        elif val == PLANE.YZ or val == "YZ":
            return "X"
        else:
            return "Y"

    @staticmethod
    @pyaedt_function_handler()
    def cs_plane_to_plane_str(val):
        """Retrieve a string for a coordinate system plane.

        Parameters
        ----------
        val :


        Returns
        -------
        str
           String for the coordinate system plane.

        """
        if val == PLANE.XY or val == "XY":
            return "XY"
        elif val == PLANE.YZ or val == "YZ":
            return "YZ"
        else:
            return "ZX"

    @staticmethod
    @pyaedt_function_handler()
    def cs_axis_str(val):
        """Retrieve a string for a coordinate system axis.

        Parameters
        ----------
        val :


        Returns
        -------
        str
            String for the coordinate system axis.

        """
        if val == AXIS.X or val == "X":
            return "X"
        elif val == AXIS.Y or val == "Y":
            return "Y"
        else:
            return "Z"

    @staticmethod
    @pyaedt_function_handler()
    def draft_type_str(val):
        """Retrieve the draft type.

        Parameters
        ----------
        val :


        Returns
        -------
        str
           Type of the draft.

        """
        if val == SWEEPDRAFT.Extended:
            return "Extended"
        elif val == SWEEPDRAFT.Round:
            return "Round"
        else:
            return "Natural"

    @staticmethod
    @pyaedt_function_handler()
    def get_mid_point(v1, v2):
        """Evaluate the midpoint between two points.

        Parameters
        ----------
        v1 : list
            List of ``[x, y, z]`` coordinates for the first point.
        v2 : list
            List of ``[x, y, z]`` coordinates for the second point.

        Returns
        -------
        list
            List of ``[x, y, z]`` coordinates for the midpoint.

        """
        m = [((i + j) / 2.0) for i, j in zip(v1, v2)]
        return m

    @staticmethod
    @pyaedt_function_handler()
    def get_triangle_area(v1, v2, v3):
        """Evaluate the area of a triangle defined by its three vertices.

        Parameters
        ----------
        v1 : list
            List of ``[x, y, z]`` coordinates for the first vertex.
        v2 : list
            List of ``[x, y, z]`` coordinates for the second vertex.
        v3 : list
            List of ``[x, y, z]`` coordinates for the third vertex.

        Returns
        -------
        float
            Area of the triangle.

        """
        a = ((v1[0] - v2[0]) ** 2 + (v1[1] - v2[1]) ** 2 + (v1[2] - v2[2]) ** 2) ** 0.5
        b = ((v2[0] - v3[0]) ** 2 + (v2[1] - v3[1]) ** 2 + (v2[2] - v3[2]) ** 2) ** 0.5
        c = ((v3[0] - v1[0]) ** 2 + (v3[1] - v1[1]) ** 2 + (v3[2] - v1[2]) ** 2) ** 0.5
        s = 0.5 * (a + b + c)
        area = (s * (s - a) * (s - b) * (s - c)) ** 0.5
        if isinstance(area, complex):
            area = area.real
        return area

    @staticmethod
    @pyaedt_function_handler()
    def v_cross(a, b):
        """Evaluate the cross product of two geometry vectors.

        Parameters
        ----------
        a : list
            List of ``[x, y, z]`` coordinates for the first vector.
        b : list
            List of ``[x, y, z]`` coordinates for the second vector.

        Returns
        -------
        list
            List of ``[x, y, z]`` coordinates for the result vector.
        """

        c = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
        return c

    @staticmethod
    @pyaedt_function_handler()
    def _v_dot(a, b):
        """Evaluate the dot product between two geometry vectors.

        Parameters
        ----------
        a : list
            List of ``[x, y, z]`` coordinates for the first vector.
        b : list
            List of ``[x, y, z]`` coordinates for the second vector.

        Returns
        -------
        float
            Result of the dot product.

        """
        if len(a) == 3:
            c = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
            return c
        elif len(a) == 2:
            c = a[0] * b[0] + a[1] * b[1]
            return c
        return False

    @staticmethod
    @pyaedt_function_handler()
    def v_dot(a, b):
        """Evaluate the dot product between two geometry vectors.

        Parameters
        ----------
        a : list
            List of ``[x, y, z]`` coordinates for the first vector.
        b : list
            List of ``[x, y, z]`` coordinates for the second vector.

        Returns
        -------
        float
            Result of the dot product.

        """
        return GeometryOperators._v_dot(a, b)

    @staticmethod
    @pyaedt_function_handler()
    def v_prod(s, v):
        """Evaluate the product between a scalar value and a vector.

        Parameters
        ----------
        s : float
            Scalar value.
        v : list
            List of values for the vector in the format ``[v1, v2,..., vn]``.
            The vector can be any length.

        Returns
        -------
        list
            List of values for the result vector. This list is the
            same length as the list for the input vector.

        """
        r = [s * i for i in v]
        return r

    @staticmethod
    @pyaedt_function_handler()
    def v_sub(a, b):
        """Evaluate two geometry vectors by subtracting them (a-b).

        Parameters
        ----------
        a : list
            List of ``[x, y, z]`` coordinates for the first vector.
        b : list
            List of ``[x, y, z]`` coordinates for the second vector.

        Returns
        -------
        list
            List of ``[x, y, z]`` coordinates for the result vector.

        """
        c = [i - j for i, j in zip(a, b)]
        return c

    @staticmethod
    @pyaedt_function_handler()
    def v_sum(a, b):
        """Evaluate two geometry vectors by adding them (a+b).

        Parameters
        ----------
        a : list
            List of ``[x, y, z]`` coordinates for the first vector.
        b : list
            List of ``[x, y, z]`` coordinates for the second vector.

        Returns
        -------
        list
            List of ``[x, y, z]`` coordinates for the result vector.

        """
        c = [i + j for i, j in zip(a, b)]
        return c

    @staticmethod
    @pyaedt_function_handler()
    def v_norm(a):
        """Evaluate the Euclidean norm of a geometry vector.

        Parameters
        ----------
         a : list
            List of ``[x, y, z]`` coordinates for the vector.

        Returns
        -------
        float
            Evaluated norm in the same unit as the coordinates for the input vector.

        """
        t = 0
        for i in a:
            t += i**2
        m = t**0.5
        return m

    @staticmethod
    @pyaedt_function_handler()
    def normalize_vector(v):
        """Normalize a geometry vector.

        Parameters
        ----------
        v : list
            List of ``[x, y, z]`` coordinates for vector.

        Returns
        -------
        list
            List of ``[x, y, z]`` coordinates for the normalized vector.

        """
        # normalize a vector to its norm
        norm = GeometryOperators.v_norm(v)
        vn = [i / norm for i in v]
        return vn

    @staticmethod
    @pyaedt_function_handler()
    def v_points(p1, p2):
        """Vector from one point to another point.

        Parameters
        ----------
        p1 : list
            Coordinates ``[x1,y1,z1]`` for the first point.
        p2 : list
            Coordinates ``[x2,y2,z2]`` for second point.

        Returns
        -------
        List
            Coordinates ``[vx, vy, vz]`` for the vector from the first point to the second point.
        """
        return GeometryOperators.v_sub(p2, p1)

    @staticmethod
    @pyaedt_function_handler()
    def points_distance(p1, p2):
        """Evaluate the distance between two points expressed as their Cartesian coordinates.

        Parameters
        ----------
        p1 : list
            List of ``[x1,y1,z1]`` coordinates for the first point.
        p2 : list
            List of ``[x2,y2,z2]`` coordinates for the second ppint.

        Returns
        -------
        float
            Distance between the two points in the same unit as the coordinates for the points.

        """
        # fmt: off
        if len(p1) == 3:
            return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)
        elif len(p1) == 2:
            return math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        return False
        # fmt: on

    @staticmethod
    @pyaedt_function_handler()
    def find_point_on_plane(pointlists, direction=0):
        """Find a point on a plane.

        Parameters
        ----------
        pointlists : list
            List of points.
        direction : int, optional
             The default is ``0``.

        Returns
        -------
        list

        """

        if direction <= 2:
            point = 1e6
            for p in pointlists:
                if p[direction] < point:
                    point = p[direction]
        else:
            point = -1e6
            for p in pointlists:
                if p[direction - 3] > point:
                    point = p[direction - 3]
        return point

    @staticmethod
    @pyaedt_function_handler()
    def distance_vector(p, a, b):
        """Evaluate the vector distance between point ``p`` and a line defined by two points, ``a`` and ``b``.

        .. note::
            he formula is  ``d = (a-p)-((a-p)dot p)n``, where ``a`` is a point of the line (either ``a`` or ``b``)
            and ``n`` is the unit vector in the direction of the line.

        Parameters
        ----------
        p : list
            List of ``[x, y, z]`` coordinates for the reference point.
        a : list
            List of ``[x, y, z]`` coordinates for the first point of the segment.
        b : list
            List of ``[x, y, z]`` coordinates for the second point of the segment.

        Returns
        -------
        list
            List of ``[x, y, z]`` coordinates for the distance vector.

        """
        v1 = GeometryOperators.v_points(a, b)
        n = [i / GeometryOperators.v_norm(v1) for i in v1]
        v2 = GeometryOperators.v_sub(a, p)
        s1 = GeometryOperators._v_dot(v2, n)
        v3 = [i * s1 for i in n]
        vd = GeometryOperators.v_sub(v2, v3)
        return vd

    @staticmethod
    @pyaedt_function_handler()
    def is_between_points(p, a, b, tol=1e-6):
        """Check if a point lies on the segment defined by two points.

        Parameters
        ----------
        p : list
            List of ``[x, y, z]`` coordinates for the reference point ``p``.
        a : list
            List of ``[x, y, z]`` coordinates for the first point of the segment.
        b : list
            List of ``[x, y, z]`` coordinates for the second point of the segment.
        tol : float
            Linear tolerance. The default value is ``1e-6``.

        Returns
        -------
        bool
            ``True`` when the point lies on the segment defined by the two points, ``False`` otherwise.

        """
        v1 = GeometryOperators.v_points(a, b)
        v2 = GeometryOperators.v_points(a, p)
        if abs(GeometryOperators.v_norm(GeometryOperators.v_cross(v1, v2))) > tol:
            return False  # not collinear
        t1 = GeometryOperators._v_dot(v1, v2)
        t2 = GeometryOperators._v_dot(v1, v1)
        if t1 < 0 or t1 > t2:
            return False
        else:
            return True

    @staticmethod
    @pyaedt_function_handler()
    def is_parallel(a1, a2, b1, b2, tol=1e-6):
        """Check if a segment defined by two points is parallel to a segment defined by two other points.

        Parameters
        ----------
        a1 : list
            List of ``[x, y, z]`` coordinates for the first point of the fiirst segment.
        a2 : list
            List of ``[x, y, z]`` coordinates for the second point of the first segment.
        b1 : list
            List of ``[x, y, z]`` coordinates for the first point of the second segment.
        b2 : list
            List of ``[x, y, z]`` coordinates for the second point of the second segment.
        tol : float
            Linear tolerance. The default value is ``1e-6``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if 1.0 - GeometryOperators.parallel_coeff(a1, a2, b1, b2) < tol * tol:
            return True
        else:
            return False

    @staticmethod
    @pyaedt_function_handler()
    def parallel_coeff(a1, a2, b1, b2):
        """ADD DESCRIPTION.

        Parameters
        ----------
        a1 : list
            List of ``[x, y, z]`` coordinates for the first point of the first segment.
        a2 : list
            List of ``[x, y, z]`` coordinates for the second point of the first segment.
        b1 : list
            List of ``[x, y, z]`` coordinates for the first point of the second segment.
        b2 : list
            List of ``[x, y, z]`` coordinates for the second point of the second segment.

        Returns
        -------
        float
            _vdot of 4 vertices of 2 segments.
        """
        va = GeometryOperators.v_points(a1, a2)
        vb = GeometryOperators.v_points(b1, b2)
        an = GeometryOperators.v_norm(va)
        bn = GeometryOperators.v_norm(vb)
        var = GeometryOperators._v_dot(va, vb) / (an * bn)
        return abs(var)

    @staticmethod
    @pyaedt_function_handler()
    def is_collinear(a, b, tol=1e-6):
        """Check if two vectors are collinear (parallel or anti-parallel).

        Parameters
        ----------
        a : list
            List of ``[x, y, z]`` coordinates for the first vector.
        b : list
            List of ``[x, y, z]`` coordinates for the second vector.
        tol : float
            Linear tolerance. The default value is ``1e-6``.

        Returns
        -------
        bool
            ``True`` if vectors are collinear, ``False`` otherwise.

        """
        an = GeometryOperators.v_norm(a)
        bn = GeometryOperators.v_norm(b)
        var = GeometryOperators._v_dot(a, b) / (an * bn)
        if 1.0 - abs(var) < tol * tol:
            return True
        else:
            return False

    @staticmethod
    @pyaedt_function_handler()
    def is_projection_inside(a1, a2, b1, b2):
        """Project a segment onto another segment and check if the projected segment is inside it.

        Parameters
        ----------
        a1 : list
            List of ``[x, y, z]`` coordinates for the first point of the projected segment.
        a2 : list
            List of ``[x, y, z]`` coordinates for the second point of the projected segment.
        b1 : list
            List of ``[x, y, z]`` coordinates for the first point of the other segment.
        b2 : list
            List of ``[x, y, z]`` coordinates for the second point of the other segment.

        Returns
        -------
        bool
            ``True`` when the projected segment is inside the other segmennt, ``False`` otherwise.

        """
        if not GeometryOperators.is_parallel(a1, a2, b1, b2):
            return False
        d = GeometryOperators.distance_vector(a1, b1, b2)
        a1n = GeometryOperators.v_sum(a1, d)
        a2n = GeometryOperators.v_sum(a2, d)
        if not GeometryOperators.is_between_points(a1n, b1, b2):
            return False
        if not GeometryOperators.is_between_points(a2n, b1, b2):
            return False
        return True

    @staticmethod
    @pyaedt_function_handler()
    def arrays_positions_sum(vertlist1, vertlist2):
        """ADD DESCRIPTION.

        Parameters
        ----------
        vertlist1 : list

        vertlist2 : list

        Returns
        -------
        float

        """
        s = 0
        for el in vertlist1:
            for el1 in vertlist2:
                s += GeometryOperators.points_distance(el, el1)
        return s / (len(vertlist1) + len(vertlist2))

    @staticmethod
    @pyaedt_function_handler()
    def v_angle(a, b):
        """Evaluate the angle between two geometry vectors.

        Parameters
        ----------
        a : list
            List of ``[x, y, z]`` coordinates for the first vector.
        b : list
            List of ``[x, y, z]`` coordinates for the second vector.

        Returns
        -------
        float
            Angle in radians.

        """
        d = GeometryOperators.v_dot(a, b)
        an = GeometryOperators.v_norm(a)
        bn = GeometryOperators.v_norm(b)
        if (an * bn) == 0.0:
            return 0.0
        else:
            return math.acos(d / (an * bn))

    @staticmethod
    @pyaedt_function_handler()
    def pointing_to_axis(x_pointing, y_pointing):
        """Retrieve the axes from the HFSS X axis and Y pointing axis as per
        the definition of the AEDT interface coordinate system.

        Parameters
        ----------
        x_pointing : list
            List of ``[x, y, z]`` coordinates for the X axis.

        y_pointing : list
            List of ``[x, y, z]`` coordinates for the Y pointing axis.

        Returns
        -------
        tuple
            ``[Xx, Xy, Xz], [Yx, Yy, Yz], [Zx, Zy, Zz]`` of the three axes (normalized).
        """

        xp = GeometryOperators.normalize_vector(x_pointing)

        tp = GeometryOperators.v_dot(y_pointing, xp)
        ypt = GeometryOperators.v_sub(y_pointing, GeometryOperators.v_prod(tp, xp))
        yp = GeometryOperators.normalize_vector(ypt)

        zpt = GeometryOperators.v_cross(xp, yp)
        zp = GeometryOperators.normalize_vector(zpt)

        return xp, yp, zp

    @staticmethod
    @pyaedt_function_handler()
    def axis_to_euler_zxz(x, y, z):
        """Retrieve the Euler angles of a frame defined by X, Y, and Z axes, following the rotation sequence ZXZ.

        Provides assumption for the gimbal lock problem.

        Parameters
        ----------
        x : list
            List of ``[Xx, Xy, Xz]`` coordinates for the X axis.
        y : list
            List of ``[Yx, Yy, Yz]`` coordinates for the Y axis.
        z : list
            List of ``[Zx, Zy, Zz]`` coordinates for the Z axis.

        Returns
        -------
        tuple
            (phi, theta, psi) containing the Euler angles in radians.

        """
        x1 = x[0]
        x2 = x[1]
        x3 = x[2]
        y3 = y[2]
        z1 = z[0]
        z2 = z[1]
        z3 = z[2]
        if z == [0, 0, 1]:
            phi = GeometryOperators.atan2(x2, x1)
            theta = 0.0
            psi = 0.0
        elif z == [0, 0, -1]:
            phi = GeometryOperators.atan2(x2, x1)
            theta = math.pi
            psi = 0.0
        else:
            phi = GeometryOperators.atan2(z1, -z2)
            theta = math.acos(z3)
            psi = GeometryOperators.atan2(x3, y3)
        return phi, theta, psi

    @staticmethod
    @pyaedt_function_handler()
    def axis_to_euler_zyz(x, y, z):
        """Retrieve the Euler angles of a frame defined by X, Y, and Z axes, following rotation sequence ZYZ.

        Provides assumption for the gimbal lock problem.

        Parameters
        ----------
        x : list
            List of ``[Xx, Xy, Xz]`` coordinates for the X axis.
        y : list
            List of ``[Yx, Yy, Yz]`` coordinates for the Y axis.
        z : list
            List of ``[Zx, Zy, Zz]`` coordinates for the Z axis.

        Returns
        -------
        tuple
            (phi, theta, psi) containing the Euler angles in radians.

        """
        x1 = x[0]
        x2 = x[1]
        x3 = x[2]
        y3 = y[2]
        z1 = z[0]
        z2 = z[1]
        z3 = z[2]
        if z == [0, 0, 1]:
            phi = GeometryOperators.atan2(x2, x1)
            theta = 0.0
            psi = 0.0
        elif z == [0, 0, -1]:
            phi = GeometryOperators.atan2(x2, x1)
            theta = math.pi
            psi = 0.0
        else:
            phi = GeometryOperators.atan2(z2, z1)
            theta = math.acos(z3)
            psi = GeometryOperators.atan2(y3, -x3)
        return phi, theta, psi

    @staticmethod
    @pyaedt_function_handler()
    def quaternion_to_axis(q):
        """Convert a quaternion to a rotated frame defined by X, Y, and Z axes.

        Parameters
        ----------
        q : list
            List of ``[q1, q2, q3, q4]`` coordinates for the quaternion.

        Returns
        -------
        tuple
            [Xx, Xy, Xz], [Yx, Yy, Yz], [Zx, Zy, Zz] of the three axes (normalized).

        """
        q1 = q[0]
        q2 = q[1]
        q3 = q[2]
        q4 = q[3]

        m11 = q1 * q1 + q2 * q2 - q3 * q3 - q4 * q4
        m12 = 2.0 * (q2 * q3 - q1 * q4)
        m13 = 2.0 * (q2 * q4 + q1 * q3)

        m21 = 2.0 * (q2 * q3 + q1 * q4)
        m22 = q1 * q1 - q2 * q2 + q3 * q3 - q4 * q4
        m23 = 2.0 * (q3 * q4 - q1 * q2)

        m31 = 2.0 * (q2 * q4 - q1 * q3)
        m32 = 2.0 * (q3 * q4 + q1 * q2)
        m33 = q1 * q1 - q2 * q2 - q3 * q3 + q4 * q4

        x = GeometryOperators.normalize_vector([m11, m21, m31])
        y = GeometryOperators.normalize_vector([m12, m22, m32])
        z = GeometryOperators.normalize_vector([m13, m23, m33])

        return x, y, z

    @staticmethod
    @pyaedt_function_handler()
    def quaternion_to_axis_angle(q):
        """Convert a quaternion to the axis angle rotation formulation.

        Parameters
        ----------
        q : list
            List of ``[q1, q2, q3, q4]`` coordinates for the quaternion.

        Returns
        -------
        tuple
            ([ux, uy, uz], theta) containing the rotation axes expressed as X, Y, Z components of the unit vector ``u``
            and the rotation angle theta expressed in radians.

        """
        q1 = q[0]
        q2 = q[1]
        q3 = q[2]
        q4 = q[3]
        n = (q2 * q2 + q3 * q3 + q4 * q4) ** 0.5
        u = [q2 / n, q3 / n, q4 / n]
        theta = 2.0 * GeometryOperators.atan2(n, q1)
        return u, theta

    @staticmethod
    @pyaedt_function_handler()
    def axis_angle_to_quaternion(u, theta):
        """Convert the axis angle rotation formulation to a quaternion.

        Parameters
        ----------
        u : list
            List of ``[ux, uy, uz]`` coordinates for the rotation axis.

        theta : float
            Angle of rotation in radians.

        Returns
        -------
        list
            List of ``[q1, q2, q3, q4]`` coordinates for the quaternion.

        """
        un = GeometryOperators.normalize_vector(u)
        s = math.sin(theta * 0.5)
        q1 = math.cos(theta * 0.5)
        q2 = un[0] * s
        q3 = un[1] * s
        q4 = un[2] * s
        return [q1, q2, q3, q4]

    @staticmethod
    @pyaedt_function_handler()
    def quaternion_to_euler_zxz(q):
        """Convert a quaternion to Euler angles following rotation sequence ZXZ.

        Parameters
        ----------
        q : list
            List of ``[q1, q2, q3, q4]`` coordinates for the quaternion.

        Returns
        -------
        tuple
            (phi, theta, psi) containing the Euler angles in radians.

        """
        q1 = q[0]
        q2 = q[1]
        q3 = q[2]
        q4 = q[3]
        m13 = 2.0 * (q2 * q4 + q1 * q3)
        m23 = 2.0 * (q3 * q4 - q1 * q2)
        m33 = q1 * q1 - q2 * q2 - q3 * q3 + q4 * q4
        m31 = 2.0 * (q2 * q4 - q1 * q3)
        m32 = 2.0 * (q3 * q4 + q1 * q2)
        phi = GeometryOperators.atan2(m13, -m23)
        theta = GeometryOperators.atan2((1.0 - m33 * m33) ** 0.5, m33)
        psi = GeometryOperators.atan2(m31, m32)
        return phi, theta, psi

    @staticmethod
    @pyaedt_function_handler()
    def euler_zxz_to_quaternion(phi, theta, psi):
        """Convert the Euler angles following rotation sequence ZXZ to a quaternion.

        Parameters
        ----------
        phi : float
            Euler angle psi in radians.
        theta : float
            Euler angle theta in radians.
        psi : float
            Euler angle phi in radians.

        Returns
        -------
        list
            List of ``[q1, q2, q3, q4]`` coordinates for the quaternion.

        """
        t1 = phi
        t2 = theta
        t3 = psi
        c = math.cos(t2 * 0.5)
        s = math.sin(t2 * 0.5)
        q1 = c * math.cos((t1 + t3) * 0.5)
        q2 = s * math.cos((t1 - t3) * 0.5)
        q3 = s * math.sin((t1 - t3) * 0.5)
        q4 = c * math.sin((t1 + t3) * 0.5)
        return [q1, q2, q3, q4]

    @staticmethod
    @pyaedt_function_handler()
    def quaternion_to_euler_zyz(q):
        """Convert a quaternion to Euler angles following rotation sequence ZYZ.

        Parameters
        ----------
        q : list
            List of ``[q1, q2, q3, q4]`` coordinates for the quaternion.

        Returns
        -------
        tuple
            (phi, theta, psi) containing the Euler angles in radians.

        """
        q1 = q[0]
        q2 = q[1]
        q3 = q[2]
        q4 = q[3]
        m13 = 2.0 * (q2 * q4 + q1 * q3)
        m23 = 2.0 * (q3 * q4 - q1 * q2)
        m33 = q1 * q1 - q2 * q2 - q3 * q3 + q4 * q4
        m31 = 2.0 * (q2 * q4 - q1 * q3)
        m32 = 2.0 * (q3 * q4 + q1 * q2)
        phi = GeometryOperators.atan2(m23, m13)
        theta = GeometryOperators.atan2((1.0 - m33 * m33) ** 0.5, m33)
        psi = GeometryOperators.atan2(m32, -m31)
        return phi, theta, psi

    @staticmethod
    @pyaedt_function_handler()
    def euler_zyz_to_quaternion(phi, theta, psi):
        """Convert the Euler angles following rotation sequence ZYZ to a quaternion.

        Parameters
        ----------
        phi : float
            Euler angle psi in radians.
        theta : float
            Euler angle theta in radians.
        psi : float
            Euler angle phi in radians.

        Returns
        -------
        list
            List of ``[q1, q2, q3, q4]`` coordinates for the quaternion.

        """
        t1 = phi
        t2 = theta
        t3 = psi
        c = math.cos(t2 * 0.5)
        s = math.sin(t2 * 0.5)
        q1 = c * math.cos((t1 + t3) * 0.5)
        q2 = -s * math.sin((t1 - t3) * 0.5)
        q3 = s * math.cos((t1 - t3) * 0.5)
        q4 = c * math.sin((t1 + t3) * 0.5)
        return [q1, q2, q3, q4]

    @staticmethod
    @pyaedt_function_handler()
    def deg2rad(angle):
        """Convert the angle from degrees to radians.

        Parameters
        ----------
        angle : float
            Angle in degrees.

        Returns
        -------
        float
            Angle in radians.

        """
        pi = math.pi
        return angle / 180.0 * pi

    @staticmethod
    @pyaedt_function_handler()
    def rad2deg(angle):
        """Convert the angle from radians to degrees.

        Parameters
        ----------
        angle : float
            Angle in radians.

        Returns
        -------
        float
            Angle in degrees.

        """
        pi = math.pi
        return angle * 180.0 / pi

    @staticmethod
    @pyaedt_function_handler()
    def atan2(y, x):
        """Implementation of atan2 that does not suffer from the following issues:
        math.atan2(0.0, 0.0) = 0.0
        math.atan2(-0.0, 0.0) = -0.0
        math.atan2(0.0, -0.0) = 3.141592653589793
        math.atan2(-0.0, -0.0) = -3.141592653589793
        and returns always 0.0.

        Parameters
        ----------
        y : float
            Y-axis value for atan2.

        x : float
            X-axis value for atan2.

        Returns
        -------
        float

        """
        eps = 7.0 / 3.0 - 4.0 / 3.0 - 1.0
        if abs(y) < eps:
            y = 0.0
        if abs(x) < eps:
            x = 0.0
        return math.atan2(y, x)

    @staticmethod
    @pyaedt_function_handler()
    def q_prod(p, q):
        """Evaluate the product of two quaternions, ``p`` and ``q``, defined as:
        p = p0 + p' = p0 + ip1 + jp2 + kp3.
        q = q0 + q' = q0 + iq1 + jq2 + kq3.
        r = pq = p0q0 - p' • q' + p0q' + q0p' + p' x q'.

        Parameters
        ----------
        p : list
            List of ``[p1, p2, p3, p4]`` coordinates for quaternion ``p``.

        q : list
            List of ``[p1, p2, p3, p4]`` coordinates for quaternion ``q``.

        Returns
        -------
        list
            List of [r1, r2, r3, r4] coordinates for the result quaternion.

        """
        p0 = p[0]
        pv = p[1:4]
        q0 = q[0]
        qv = q[1:4]

        r0 = p0 * q0 - GeometryOperators.v_dot(pv, qv)

        t1 = GeometryOperators.v_prod(p0, qv)
        t2 = GeometryOperators.v_prod(q0, pv)
        t3 = GeometryOperators.v_cross(pv, qv)
        rv = GeometryOperators.v_sum(t1, GeometryOperators.v_sum(t2, t3))

        return [r0, rv[0], rv[1], rv[2]]

    @staticmethod
    @pyaedt_function_handler()
    def q_rotation(v, q):
        """Evaluate the rotation of a vector defined by a quaternion.
        Evaluated as:
        ``"q = q0 + q' = q0 + iq1 + jq2 + kq3"``,
        ``"w = qvq* = (q0^2 - |q'|^2)v + 2(q' • v)q' + 2q0(q' x v)"``.

        Parameters
        ----------
        v : list
            List of ``[v1, v2, v3]`` coordinates for the vector.
        q : list
            List of ``[q1, q2, q3, q4]`` coordinates for the quaternion.

        Returns
        -------
        list
            List of ``[w1, w2, w3]`` coordinates for the result vector ``w``.
        """
        q0 = q[0]
        qv = q[1:4]

        c1 = q0 * q0 - (qv[0] * qv[0] + qv[1] * qv[1] + qv[2] * qv[2])
        t1 = GeometryOperators.v_prod(c1, v)

        c2 = 2.0 * GeometryOperators.v_dot(qv, v)
        t2 = GeometryOperators.v_prod(c2, qv)

        t3 = GeometryOperators.v_cross(qv, v)
        t4 = GeometryOperators.v_prod(2.0 * q0, t3)

        w = GeometryOperators.v_sum(t1, GeometryOperators.v_sum(t2, t4))

        return w

    @staticmethod
    @pyaedt_function_handler()
    def q_rotation_inv(v, q):
        """Evaluate the inverse rotation of a vector that is defined by a quaternion.

        It can also be the rotation of the coordinate frame with respect to the vector.

            q = q0 + q' = q0 + iq1 + jq2 + kq3
            q* = q0 - q' = q0 - iq1 - jq2 - kq3
            w = q*vq

        Parameters
        ----------
        v : list
            List of ``[v1, v2, v3]`` coordinates for the vector.

        q : list
            List of ``[q1, q2, q3, q4]`` coordinates for the quaternion.

        Returns
        -------
        list
            List of ``[w1, w2, w3]`` coordinates for the vector.

        """
        q1 = [q[0], -q[1], -q[2], -q[3]]
        return GeometryOperators.q_rotation(v, q1)

    @staticmethod
    @pyaedt_function_handler()
    def get_polygon_centroid(pts):
        """Evaluate the centroid of a polygon defined by its points.

        Parameters
        ----------
        pts : list
            List of points, with each point defined by its ``[x,y,z]`` coordinates.

        Returns
        -------
        list
            List of [x,y,z] coordinates for the centroid of the polygon.

        """
        if len(pts) == 0:  # pragma: no cover
            raise ValueError("pts must contain at list one point")
        sx = sy = sz = sl = sl2 = 0
        x1, y1, z1 = pts[0]
        for i in range(len(pts)):  # counts from 0 to len(points)-1
            x0, y0, z0 = pts[i - 1]  # in Python points[-1] is last element of points
            x1, y1, z1 = pts[i]
            L = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
            sx += (x0 + x1) / 2 * L
            sy += (y0 + y1) / 2 * L
            L2 = ((z1 - z0) ** 2 + (x1 - x0) ** 2) ** 0.5
            sz += (z0 + z1) / 2 * L2
            sl += L
            sl2 += L2
        xc = sx / sl if sl != 0.0 else x1
        yc = sy / sl if sl != 0.0 else y1
        zc = sz / sl2 if sl2 != 0.0 else z1

        return [xc, yc, zc]

    @staticmethod
    @pyaedt_function_handler()
    def cs_xy_pointing_expression(yaw, pitch, roll):
        """Return x_pointing and y_pointing vectors as expressions from
        the yaw, ptich, and roll input (as strings).

        Parameters
        ----------
        yaw : str, required
            String expression for the yaw angle (rotation about Z-axis)
        pitch : str
            String expression for the pitch angle (rotation about Y-axis)
        roll : str
            String expression for the roll angle (rotation about X-axis)

        Returns
        -------
        [x_pointing, y_pointing] vector expressions.
        """
        # X-Pointing
        xx = "cos(" + yaw + ")*cos(" + pitch + ")"
        xy = "sin(" + yaw + ")*cos(" + pitch + ")"
        xz = "sin(" + pitch + ")"

        # Y-Pointing
        yx = "sin(" + roll + ")*sin(" + pitch + ")*cos(" + yaw + ") - "
        yx += "sin(" + yaw + ")*cos(" + roll + ")"

        yy = "sin(" + roll + ")*sin(" + yaw + ")*sin(" + pitch + ") + "
        yy += "cos(" + roll + ")*cos(" + yaw + ")"

        yz = "sin(" + roll + " + pi)*cos(" + pitch + ")"  # use pi to avoid negative sign.

        # x, y pointing vectors for CS
        x_pointing = [xx, xy, xz]
        y_pointing = [yx, yy, yz]

        return [x_pointing, y_pointing]

    @staticmethod
    @pyaedt_function_handler()
    def get_numeric(s):
        """Convert a string to a numeric value. Discard the suffix."""
        if type(s) == str:
            if s == "Global":
                return 0.0
            else:
                return float("".join(c for c in s if c.isdigit() or c == "."))
        elif s is None:
            return 0.0
        else:
            return float(s)

    @staticmethod
    @pyaedt_function_handler()
    def is_small(s):
        """
        Return True if the number represented by s is zero (i.e very small).

        Parameters
        ----------
        s, numeric or str
            Variable value.

        Returns
        -------

        """
        n = GeometryOperators.get_numeric(s)
        return True if math.fabs(n) < 2.0 * abs(sys.float_info.epsilon) else False

    @staticmethod
    @pyaedt_function_handler()
    def numeric_cs(cs_in):
        """Return a list of [x,y,z] numeric values given a coordinate system as input.

        Parameters
        ----------
        cs_in : list of str or str
            ``["x", "y", "z"]`` or "Global".
        """
        if type(cs_in) is str:
            if cs_in == "Global":
                return [0.0, 0.0, 0.0]
            else:
                return None
        elif type(cs_in) is list:
            if len(cs_in) == 3:
                return [GeometryOperators.get_numeric(s) if type(s) is str else s for s in cs_in]
            else:
                return [0, 0, 0]

    @staticmethod
    @pyaedt_function_handler()
    def orient_polygon(x, y, clockwise=True):
        """
        Orient a polygon clockwise or counterclockwise. The vertices should be already ordered either way.
        Use this function to change the orientation.
        The polygon is represented by its vertices coordinates.

        Parameters
        ----------
        x : list
            List of x coordinates of the vertices. Length must be >= 3.
        y : list
            List of y coordinates of the vertices. Must be of the same length as x.
        clockwise : bool
            If ``True`` the polygon is oriented colckwise, if ``False`` it is oriented counterclockwise.
            Default is ``True``.

        Returns
        -------
        list of list
            Lists of oriented vertices.
        """
        # select a vertex on the hull
        if len(x) < 3:  # pragma: no cover
            raise ValueError("'x' length must be >= 3")
        if len(y) != len(x):  # pragma: no cover
            raise ValueError("'y' must be same length as 'x'.")
        # fmt: off
        xmin = min(x)
        ixmin = [i for i, el in enumerate(x) if xmin == el]
        if len(ixmin) == 1:
            imin = ixmin[0]
        else:  # searching for the minimum y
            tmpy = [(i, el) for i, el in enumerate(y) if i in ixmin]
            min_tmpy = min(tmpy, key=lambda t: t[1])
            imin = min_tmpy[0]
        ymin = y[imin]
        if imin == 0:  # the minimum is the first point of the polygon
            xa = x[-1]
            ya = y[-1]
            xb = xmin
            yb = ymin
            xc = x[1]
            yc = y[1]
        elif imin == len(x)-1:  # the minimum is the last point of the polygon
            xa = x[imin-1]
            ya = y[imin-1]
            xb = xmin
            yb = ymin
            xc = x[0]
            yc = y[0]
        else:
            xa = x[imin-1]
            ya = y[imin-1]
            xb = xmin
            yb = ymin
            xc = x[imin+1]
            yc = y[imin+1]
        det = (xb-xa) * (yc-ya) - (xc-xa) * (yb-ya)
        if det > 0:  # counterclockwise
            is_CW = False
        else:   # clockwise
            is_CW = True
        # fmt: on
        if (clockwise and not is_CW) or (not clockwise and is_CW):
            x.reverse()
            y.reverse()
        return x, y

    @staticmethod
    @pyaedt_function_handler()
    def v_angle_sign(va, vb, vn, right_handed=True):
        """Evaluate the signed angle between two geometry vectors.
        The sign is evaluated respect to the normal to the plane containing the two vectors as per the following rule.
        In case of opposite vectors, it returns an angle equal to 180deg (always positive).
        Assuming that the plane normal is normalized (vb == 1), the signed angle is simplified.
        For the right-handed rotation from Va to Vb:
        - atan2((va x Vb) . vn, va . vb).
        For the left-handed rotation from Va to Vb:
        - atan2((Vb x va) . vn, va . vb).

        Parameters
        ----------
        va : list
            List of ``[x, y, z]`` coordinates for the first vector.
        vb : list
            List of ``[x, y, z]`` coordinates for the second vector.
        vn : list
            List of ``[x, y, z]`` coordinates for the plane normal.
        right_handed : bool
            Whether to consider the right-handed rotation from va to vb. The default is ``True``.
            When ``False``, left-hand rotation from va to vb is considered.

        Returns
        -------
        float
            Angle in radians.

        """
        tol = 1e-12
        cross = GeometryOperators.v_cross(va, vb)
        if GeometryOperators.v_norm(cross) < tol:
            return math.pi
        assert GeometryOperators.is_collinear(cross, vn), (
            "vn must be the normal to the " "plane containing va and vb."
        )  # pragma: no cover

        vnn = GeometryOperators.normalize_vector(vn)
        if right_handed:
            return math.atan2(GeometryOperators.v_dot(cross, vnn), GeometryOperators.v_dot(va, vb))
        else:
            mcross = GeometryOperators.v_cross(vb, va)
            return math.atan2(GeometryOperators.v_dot(mcross, vnn), GeometryOperators.v_dot(va, vb))

    @staticmethod
    @pyaedt_function_handler()
    def v_angle_sign_2D(va, vb, right_handed=True):
        """Evaluate the signed angle between two 2D geometry vectors.
        Iit the 2D version of the ``GeometryOperators.v_angle_sign`` considering vn = [0,0,1].
        In case of opposite vectors, it returns an angle equal to 180deg (always positive).

        Parameters
        ----------
        va : List
            List of ``[x, y]`` coordinates for the first vector.
        vb : List
            List of ``[x, y]`` coordinates for the second vector.
        right_handed : bool
            Whether to consider the right-handed rotation from Va to Vb. The default is ``True``.
            When ``False``, left-hand rotation from Va to Vb is considered.

        Returns
        -------
        float
            Angle in radians.

        """
        c = va[0] * vb[1] - va[1] * vb[0]

        if right_handed:
            return math.atan2(c, GeometryOperators.v_dot(va, vb))
        else:
            return math.atan2(-c, GeometryOperators.v_dot(va, vb))

    @staticmethod
    @pyaedt_function_handler()
    def point_in_polygon(point, polygon):
        """Determine if a point is inside or outside a polygon, both located on the same plane.

        The method implements the radial algorithm (https://es.wikipedia.org/wiki/Algoritmo_radial)

        point : list
            List of ``[x, y]`` coordinates.
        polygon : list
            [[x1, x2, ..., xn],[y1, y2, ..., yn]]

        Returns
        -------
        int
            - ``-1`` When the point is outside the polygon.
            - ``0`` When the point is exactly on one of the sides of the polygon.
            - ``1`` When the point is inside the polygon.
        """
        # fmt: off
        tol = 1e-8
        if len(point) != 2:  # pragma: no cover
            raise ValueError("point must be a list in the form [x, y]")
        pl = len(polygon[0])
        if len(polygon[1]) != pl:  # pragma: no cover
            raise ValueError("Polygon x and y lists must be the same length")
        asum = 0
        for i in range(pl):
            vj = [polygon[0][i-1], polygon[1][i-1]]
            vi = [polygon[0][i], polygon[1][i]]
            if GeometryOperators.points_distance(point, vi) < tol:
                return 0  # point is one of polyline vertices
            vpj = GeometryOperators.v_points(point, vj)
            vpi = GeometryOperators.v_points(point, vi)
            a = GeometryOperators.v_angle_sign_2D(vpj, vpi)
            if abs(abs(a) - math.pi) < tol:
                return 0
            asum += a
        if abs(asum) < tol:
            return -1
        elif abs(abs(asum) - 2*math.pi) < tol:
            return 1
        else:  # pragma: no cover
            raise Exception("Unexpected error!")
        # fmt: on

    @staticmethod
    @pyaedt_function_handler()
    def is_point_in_polygon(point, polygon):
        """Determine if a point is inside or outside a polygon, both located on the same plane.

        The method implements the radial algorithm (https://es.wikipedia.org/wiki/Algoritmo_radial)

        point : list
            List of ``[x, y]`` coordinates.
        polygon : list
            [[x1, x2, ..., xn],[y1, y2, ..., yn]]

        Returns
        -------
        bool
            ``True`` if the point is inside the polygon or exactly on one of its sides.
            ``False`` otherwise.
        """
        r = GeometryOperators.point_in_polygon(point, polygon)
        if r == -1:
            return False
        else:
            return True

    @staticmethod
    @pyaedt_function_handler()
    def are_segments_intersecting(a1, a2, b1, b2, include_collinear=True):
        """
        Determine if the two segments a and b are intersecting.

        a1 : list
            First point of segment a. List of ``[x, y]`` coordinates.
        a2 : list
            Second point of segment a. List of ``[x, y]`` coordinates.
        b1 : list
            First point of segment b. List of ``[x, y]`` coordinates.
        b2 : list
            Second point of segment b. List of ``[x, y]`` coordinates.
        include_collinear : bool
            If ``True`` two segments are considered intersecting also if just one end lies on the other segment.
            Default is ``True``.

        Returns
        -------
        bool
            ``True`` if the segments are intersecting.
            ``False`` otherwise.
        """
        # fmt: off
        def on_segment(p, q, r):
            # Given three collinear points p, q, r, the function checks if point q lies on line-segment 'pr'
            if ((q[0] <= max(p[0], r[0])) and (q[0] >= min(p[0], r[0])) and
               (q[1] <= max(p[1], r[1])) and (q[1] >= min(p[1], r[1]))):
                return True
            return False

        def orientation(p, q, r):
            # Find the orientation of an ordered triplet (p,q,r) using the slope evaluation.
            # The function returns the following values:
            # 0 : Collinear points
            # 1 : Clockwise points
            # -1 : Counterclockwise
            val = float(q[1]-p[1]) * float(r[0]-q[0]) - float(q[0]-p[0]) * float(r[1]-q[1])
            if val > 0:
                return 1  # Clockwise orientation
            elif val < 0:
                return -1  # Counterclockwise orientation
            else:
                return 0   # Collinear orientation

        # MAIN
        # Find the 4 orientations
        o1 = orientation(a1, a2, b1)
        o2 = orientation(a1, a2, b2)
        o3 = orientation(b1, b2, a1)
        o4 = orientation(b1, b2, a2)

        # General case
        if (o1 != o2) and (o3 != o4):
            if include_collinear:
                return True
            else:
                # a1 , a2 and b1 are collinear and b1 lies on segment a1a2
                if (o1 == 0) and on_segment(a1, b1, a2):
                    return False
                # a1 , a2 and b2 are collinear and b2 lies on segment a1a2
                if (o2 == 0) and on_segment(a1, b2, a2):
                    return False
                # b1 , b2 and a1 are collinear and a1 lies on segment b1b2
                if (o3 == 0) and on_segment(b1, a1, b2):
                    return False
                # b1 , b2 and a2 are collinear and a2 lies on segment b1b2
                if (o4 == 0) and on_segment(b1, a2, b2):
                    return False
                return True

        # Special Cases
        # a1 , a2 and b1 are collinear and b1 lies on segment a1a2
        if (o1 == 0) and on_segment(a1, b1, a2):
            return include_collinear
        # a1 , a2 and b2 are collinear and b2 lies on segment a1a2
        if (o2 == 0) and on_segment(a1, b2, a2):
            return include_collinear
        # b1 , b2 and a1 are collinear and a1 lies on segment b1b2
        if (o3 == 0) and on_segment(b1, a1, b2):
            return include_collinear
        # b1 , b2 and a2 are collinear and a2 lies on segment b1b2
        if (o4 == 0) and on_segment(b1, a2, b2):
            return include_collinear
        # If none of the cases
        return False
        # fmt: on

    @staticmethod
    @pyaedt_function_handler()
    def is_segment_intersecting_polygon(a, b, polygon):
        """
        Determine if a segment defined by two points ``a`` and ``b`` intersects a polygon.
        Points on the vertices and on the polygon boundaries are not considered intersecting.

        a : list
            First point of the segment. List of ``[x, y]`` coordinates.
        b : list
            Second point of the segment. List of ``[x, y]`` coordinates.
        polygon : list
            [[x1, x2, ..., xn],[y1, y2, ..., yn]]

        Returns
        -------
        float
            ``True`` if the segment intersect the polygon. ``False`` otherwise.
        """
        assert len(a) == 2, "point must be a list in the form [x, y]"
        assert len(b) == 2, "point must be a list in the form [x, y]"
        pl = len(polygon[0])
        assert len(polygon[1]) == pl, "Polygon x and y lists must be the same length"

        a_in = GeometryOperators.is_point_in_polygon(a, polygon)
        b_in = GeometryOperators.is_point_in_polygon(b, polygon)
        if a_in != b_in:
            return True  # one point is inside and one is outside, no need for further investigation.
        for i in range(pl):
            vj = [polygon[0][i - 1], polygon[1][i - 1]]
            vi = [polygon[0][i], polygon[1][i]]
            if GeometryOperators.are_segments_intersecting(a, b, vi, vj, include_collinear=False):
                return True
        return False

    @staticmethod
    @pyaedt_function_handler()
    def is_perpendicular(a, b, tol=1e-6):
        """Check if two vectors are perpendicular.

        Parameters
        ----------
        a : list
            List of ``[x, y, z]`` coordinates for the first vector.
        b : list
            List of ``[x, y, z]`` coordinates for the second vector.
        tol : float
            Linear tolerance. The default value is ``1e-6``.

        Returns
        -------
        bool
            ``True`` if vectors are perpendicular, ``False`` otherwise.

        """
        var = GeometryOperators._v_dot(a, b)
        if abs(var) < tol * tol:
            return True
        else:
            return False

    @staticmethod
    @pyaedt_function_handler()
    def is_point_projection_in_segment(p, a, b):
        """Check if a point projection lies on the segment defined by two points.

        Parameters
        ----------
        p : list
            List of ``[x, y, z]`` coordinates for the reference point ``p``.
        a : list
            List of ``[x, y, z]`` coordinates for the first point of the segment.
        b : list
            List of ``[x, y, z]`` coordinates for the second point of the segment.

        Returns
        -------
        bool
            ``True`` when the projection point lies on the segment defined by the two points, ``False`` otherwise.

        """
        # fmt: off
        dx = b[0]-a[0]
        dy = b[1]-a[1]
        inner_product = (p[0]-a[0])*dx + (p[1]-a[1])*dy
        return 0 <= inner_product <= dx*dx + dy*dy
        # fmt: on

    @staticmethod
    @pyaedt_function_handler()
    def point_segment_distance(p, a, b):
        """Calculate the distance between a point ``p`` and a segment defined by two points ``a`` and ``b``.

        Parameters
        ----------
        p : list
            List of ``[x, y, z]`` coordinates for the reference point ``p``.
        a : list
            List of ``[x, y, z]`` coordinates for the first point of the segment.
        b : list
            List of ``[x, y, z]`` coordinates for the second point of the segment.

        Returns
        -------
        float
            Distance between the point and the segment.
        """
        # fmt: off
        den = math.sqrt((b[0] - a[0])**2 + (b[1] - a[1])**2)
        num = (b[0] - a[0])*(a[1] - p[1]) - (a[0] - p[0])*(b[1] - a[1])
        d = abs(num)/den
        return d
        # fmt: on

    @staticmethod
    @pyaedt_function_handler()
    def find_largest_rectangle_inside_polygon(polygon, partition_max_order=16):
        """Find the largest area rectangles of arbitrary orientation in a polygon.

        Implements the algorithm described by Rubén Molano, et al.
        *"Finding the largest area rectangle of arbitrary orientation in a closed contour"*, published in
        *Applied Mathematics and Computation*.
        https://doi.org/10.1016/j.amc.2012.03.063.
        (https://www.sciencedirect.com/science/article/pii/S0096300312003207)

        Parameters
        ----------
        polygon : list
            [[x1, x2, ..., xn],[y1, y2, ..., yn]]
        partition_max_order : float, optional
            Order of the lattice partition used to find the quasi-lattice polygon that approximates ``polygon``.
            Default is ``16``.

        Returns
        -------
        list of list
            List containing the rectangles points. Return all rectangles found.
            List is in the form: [[[x1, y1],[x2, y2],...],[[x1, y1],[x2, y2],...],...].
        """

        # fmt: off
        def evaluate_partition_size(polygon, partition_max_order):
            x, y = polygon
            max_size = max(max(x)-min(x), max(y)-min(y))
            L = max_size/partition_max_order
            return L

        def build_s_ploygon_points(vertices, L):
            x, y = vertices

            # build the lattice
            xmin = min(x)
            r = int(math.ceil(float(max(x)-xmin)/L))
            ymin = min(y)
            s = int(math.ceil(float(max(y)-ymin)/L))

            # get the lattice points S inside the polygon
            Spoints = []
            for i in range(r + 1):
                xi = xmin + L * i
                for j in range(s + 1):
                    yj = ymin + L * j
                    if GeometryOperators.is_point_in_polygon([xi, yj], [x, y]):
                        Spoints.append([xi, yj])
            return Spoints

        def build_u_matrix(S, polygon):
            N = len(S)
            # preallocate the matrix
            Umatrix = [[None for j in range(N)] for i in range(N)]
            for i in range(N):
                for j in range(N):
                    if i >= j:
                        Umatrix[i][j] = 0
                    else:
                        if GeometryOperators.is_segment_intersecting_polygon(S[i], S[j], polygon):
                            Umatrix[i][j] = 0
                        else:
                            p = GeometryOperators.get_mid_point(S[i], S[j])
                            if not GeometryOperators.is_point_in_polygon(p, polygon):
                                Umatrix[i][j] = 0
                            else:
                                Umatrix[i][j] = GeometryOperators.v_points(S[i], S[j])
            return Umatrix

        def inside(i, j):
            if U[i][j] == 0 and isinstance(U[i][j], int):
                return False
            else:
                return True

        def compute_largest_rectangle(S):
            max_area = 0
            rectangles = []
            N = len(S)
            for i in range(N-3):
                for j in range(i+1, N-2):
                    if inside(i, j):
                        for k in range(j+1, N-1):
                            if inside(i, k) and GeometryOperators.is_perpendicular(U[i][j], U[i][k]):
                                ps = GeometryOperators.v_sum(GeometryOperators.v_sub(S[j], S[i]), S[k])
                                try:
                                    s = S.index(ps)
                                except ValueError:
                                    break
                                if inside(k, s) and inside(j, s):
                                    area = GeometryOperators.v_norm(U[i][j]) * GeometryOperators.v_norm(U[i][k])
                                    if area > max_area:
                                        max_area = area
                                        R = [S[i], S[j], S[s], S[k]]
                                        rectangles = [R]
                                    elif area == max_area:
                                        R = [S[i], S[j], S[s], S[k]]
                                        rectangles.append(R)
            return rectangles

        L = evaluate_partition_size(polygon, partition_max_order=partition_max_order)
        S = build_s_ploygon_points(polygon, L)
        U = build_u_matrix(S, polygon)
        R = compute_largest_rectangle(S)
        return R
        # fmt: on

    @staticmethod
    @pyaedt_function_handler()
    def degrees_over_rounded(angle, digits):
        """Ceil of angle.

        Parameters
        ----------
        angle : float
            Angle in radians which will be converted to degrees and will be over-rounded to the next "digits" decimal.
        digits : int
            Integer number which is the number of decimals.

        Returns
        -------
        float

        """
        return math.ceil(math.degrees(angle) * 10**digits) / (10**digits)

    @staticmethod
    @pyaedt_function_handler()
    def radians_over_rounded(angle, digits):
        """Radian angle ceiling.

        Parameters
        ----------
        angle : float
            Angle in degrees which will be converted to radians and will be over-rounded to the  next "digits" decimal.
        digits : int
            Integer number which is the number of decimals.

        Returns
        -------
        float

        """
        return math.ceil(math.radians(angle) * 10**digits) / (10**digits)

    @staticmethod
    @pyaedt_function_handler()
    def degrees_default_rounded(angle, digits):
        """Convert angle to degree with given digits rounding.

        Parameters
        ----------
        angle : float
            Angle in radians which will be converted to degrees and will be under-rounded to the next "digits" decimal.
        digits : int
            Integer number which is the number of decimals.

        Returns
        -------
        float

        """
        return math.floor(math.degrees(angle) * 10**digits) / (10**digits)

    @staticmethod
    @pyaedt_function_handler()
    def radians_default_rounded(angle, digits):
        """Convert to radians with given round.

        Parameters
        ----------
        angle : float
            Angle in degrees which will be converted to radians and will be under-rounded to the next "digits" decimal.
        digits : int
            Integer number which is the number of decimals.

        Returns
        -------
        float

        """
        return math.floor(math.radians(angle) * 10**digits) / (10**digits)
