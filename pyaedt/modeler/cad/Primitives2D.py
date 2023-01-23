from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.cad.Primitives import Primitives


class Primitives2D(Primitives, object):
    """Manages primitives in 2D tools.

    This class is inherited in the caller application and is accessible through the primitives variable part
    of the modeler object (for example, ``hfss.modeler`` or ``icepak.modeler``).


    Examples
    --------
    Basic usage demonstrated with a Q2D or Maxwell 2D design:

    >>> from pyaedt import Q2d
    >>> aedtapp = Q2d()
    >>> prim = aedtapp.modeler
    """

    @property
    def plane2d(self):
        """Create a 2D plane."""
        plane = "Z"
        if self._app.design_type == "Maxwell 2D":
            if self._app._odesign.GetGeometryMode() == "about Z":
                plane = "Y"
        return plane

    def __init__(self):
        Primitives.__init__(self)

    @pyaedt_function_handler()
    def create_circle(self, position, radius, num_sides=0, is_covered=True, name=None, matname=None):
        """Create a circle.

        Parameters
        ----------
        position : list
            ApplicationName.modeler.Position(x,y,z) object
        radius : float
            Radius of the object.
        numSides : int, optional
            Number of sides. The default is ``0``, which is correct for a circle.
        is_covered : bool
            Specify whether the ellipse is a sheet (covered) or a line object
        name : str, optional
            Name of the object. The default is ``None``. If ``None`` ,
            a unique name ``"NewObject_xxxxxx"`` will be assigned)
        matname : str, optional
            Name of the material. The default is ``None``. If ``None``,
            the default material is assigned.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.Object3d`
            3D object.

        References
        ----------

        >>> oEditor.CreateCircle

        Examples
        --------
        >>> circle1 = aedtapp.modeler.create_circle([0, -2, -2], 3)
        >>> circle2 = aedtapp.modeler.create_circle(position=[0, -2, -2], radius=3, num_sides=6,
        ...                                         name="MyCircle", matname="Copper")


        """
        szAxis = self.plane2d
        XCenter, YCenter, ZCenter = self._pos_with_arg(position)
        Radius = self._arg_with_dim(radius)

        vArg1 = ["NAME:CircleParameters"]
        vArg1.append("IsCovered:="), vArg1.append(is_covered)
        vArg1.append("XCenter:="), vArg1.append(XCenter)
        vArg1.append("YCenter:="), vArg1.append(YCenter)
        vArg1.append("ZCenter:="), vArg1.append(ZCenter)
        vArg1.append("Radius:="), vArg1.append(Radius)
        vArg1.append("WhichAxis:="), vArg1.append(szAxis)
        vArg1.append("NumSegments:="), vArg1.append("{}".format(num_sides))

        vArg2 = self._default_object_attributes(name=name, matname=matname)
        new_object_name = self.oeditor.CreateCircle(vArg1, vArg2)
        return self._create_object(new_object_name)

    @pyaedt_function_handler()
    def create_ellipse(self, position, major_radius, ratio, is_covered=True, name=None, matname=None):
        """Create an ellipse.

        Parameters
        ----------
        position : list of float
            Center Position of the ellipse
        major_radius : flost
            Length of the major axis of the ellipse
        ratio : float
            Ratio of the major axis to the minor axis of the ellipse
        is_covered : bool
            Specify whether the ellipse is a sheet (covered) or a line object
        name : str, default=None
            Name of the object. The default is ``None``. If ``None`` ,
            a unique name NewObject_xxxxxx will be assigned)
        matname : str, default=None
             Name of the material. The default is ``None``. If ``None``,
             the default material is assigned.

        Returns
        -------
        pyaedt.modeler.object3d.Object3d
            Object 3d.

        References
        ----------

        >>> oEditor.CreateEllipse

        Examples
        --------
        >>> ellipse1 = aedtapp.modeler.create_ellipse([0, -2, -2], 4.0, 0.2)
        >>> ellipse2 = aedtapp.modeler.create_ellipse(position=[0, -2, -2], major_radius=4.0, ratio=0.2,
        ...                                           name="MyEllipse", matname="Copper")
        """
        szAxis = self.plane2d
        XStart, YStart, ZStart = self._pos_with_arg(position)

        vArg1 = ["NAME:EllipseParameters"]
        vArg1.append("IsCovered:="), vArg1.append(is_covered)
        vArg1.append("XCenter:="), vArg1.append(XStart)
        vArg1.append("YCenter:="), vArg1.append(YStart)
        vArg1.append("ZCenter:="), vArg1.append(ZStart)
        vArg1.append("MajRadius:="), vArg1.append(self._arg_with_dim(major_radius))
        vArg1.append("Ratio:="), vArg1.append(ratio)
        vArg1.append("WhichAxis:="), vArg1.append(szAxis)

        vArg2 = self._default_object_attributes(name=name, matname=matname)
        new_object_name = self.oeditor.CreateEllipse(vArg1, vArg2)
        return self._create_object(new_object_name)

    @pyaedt_function_handler()
    def create_rectangle(self, position, dimension_list, is_covered=True, name=None, matname=None):
        """Create a rectangle.

        Parameters
        ----------
        position : list of float
            Position of the lower-left corner of the rectangle
        dimension_list : list of float
            List of rectangle sizes: [X size, Y size] for XY planes or [Z size, R size] for RZ planes
        is_covered : bool
            Specify whether the ellipse is a sheet (covered) or a line object
        name : str, default=None
            Name of the object. The default is ``None``. If ``None`` ,
            a unique name NewObject_xxxxxx will be assigned)
        matname : str, default=None
             Name of the material. The default is ``None``. If ``None``,
             the default material is assigned.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.Object3d`

        References
        ----------

        >>> oEditor.CreateRectangle

        Examples
        --------

        >>> rect1 = aedtapp.modeler.create_rectangle([0, -2, -2], [3, 4])
        >>> rect2 = aedtapp.modeler.create_rectangle(position=[0, -2, -2], dimension_list=[3, 4],
        ...                                          name="MyCircle", matname="Copper")

        """
        axis = self.plane2d
        x_start, y_start, z_start = self._pos_with_arg(position)
        width = self._arg_with_dim(dimension_list[0])
        height = self._arg_with_dim(dimension_list[1])

        vArg1 = ["NAME:RectangleParameters"]
        vArg1.append("IsCovered:="), vArg1.append(is_covered)
        vArg1.append("XStart:="), vArg1.append(x_start)
        vArg1.append("YStart:="), vArg1.append(y_start)
        vArg1.append("ZStart:="), vArg1.append(z_start)
        vArg1.append("Width:="), vArg1.append(width)
        vArg1.append("Height:="), vArg1.append(height)
        vArg1.append("WhichAxis:="), vArg1.append(axis)

        vArg2 = self._default_object_attributes(name=name, matname=matname)
        new_object_name = self.oeditor.CreateRectangle(vArg1, vArg2)
        return self._create_object(new_object_name)

    @pyaedt_function_handler()
    def create_regular_polygon(self, position, start_point, num_sides=6, is_covered=True, name=None, matname=None):
        """Create a rectangle.

        Parameters
        ----------
        position : list of float
            Position of the center of the polygon in ``[x, y, z]``.
        start_point : list of float
            Start point for the outer path of the polygon in ``[x, y, z]``.
        num_sides : int
            Number of sides of the polygon. Must be an integer >= 3.
        is_covered : bool
            Specify whether the ellipse is a sheet (covered) or a line object
        name : str, default=None
            Name of the object. The default is ``None``. If ``None`` ,
            a unique name NewObject_xxxxxx will be assigned)
        matname : str, default=None
             Name of the material. The default is ``None``. If ``None``,
             the default material is assigned.

        Returns
        -------
        pyaedt.modeler.object3d.Object3d

        References
        ----------

        >>> oEditor.CreateRegularPolygon

        Examples
        --------

        >>> pg1 = aedtapp.modeler.create_regular_polygon([0, 0, 0], [0, 2, 0])
        >>> pg2 = aedtapp.modeler.create_regular_polygon(position=[0, 0, 0], start_point=[0, 2, 0],
        ...                                              name="MyPolygon", matname="Copper")

        """
        x_center, y_center, z_center = self._pos_with_arg(position)
        x_start, y_start, z_start = self._pos_with_arg(start_point)

        n_sides = int(num_sides)
        assert n_sides > 2

        vArg1 = ["NAME:RegularPolygonParameters"]
        vArg1.append("XCenter:="), vArg1.append(x_center)
        vArg1.append("YCenter:="), vArg1.append(y_center)
        vArg1.append("ZCenter:="), vArg1.append(z_center)
        vArg1.append("XStart:="), vArg1.append(x_start)
        vArg1.append("YStart:="), vArg1.append(y_start)
        vArg1.append("ZStart:="), vArg1.append(z_start)

        vArg1.append("NumSides:="), vArg1.append(n_sides)
        vArg1.append("WhichAxis:="), vArg1.append(self.plane2d)

        vArg2 = self._default_object_attributes(name=name, matname=matname)
        new_object_name = self.oeditor.CreateRegularPolygon(vArg1, vArg2)
        return self._create_object(new_object_name)

    @pyaedt_function_handler()
    def create_region(self, pad_percent=300, is_percentage=True):
        """Create an air region.

        Parameters
        ----------
        pad_percent : float, str, list of floats or list of str, optional
            Same padding is applied if not a list. The default is ``300``.
            If a list of floats or str, interpret as adding for ``["+X", "+Y", "-X", "-Y"]``.
        is_percentage : bool, optional
            Region definition in percentage or absolute value. The default is `True``.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.Object3d`
            Region object.

        References
        ----------

        >>> oEditor.CreateRegion
        """
        if not isinstance(pad_percent, list):
            if self._app.xy_plane:
                pad_percent = [pad_percent, pad_percent, 0, pad_percent, pad_percent, 0]
            else:
                pad_percent = [pad_percent, 0, pad_percent, pad_percent, 0, pad_percent]

        else:
            if self._app.xy_plane:
                pad_percent = [pad_percent[0], pad_percent[1], 0, pad_percent[2], pad_percent[3], 0]

            else:
                pad_percent = [pad_percent[0], 0, pad_percent[1], pad_percent[2], 0, pad_percent[3]]

        return Primitives.create_region(self, pad_percent, is_percentage)
