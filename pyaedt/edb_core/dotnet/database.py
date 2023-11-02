"""Database."""
import os
import re
import sys

from pyaedt import __version__
from pyaedt.aedt_logger import pyaedt_logger
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.generic.general_methods import env_path, env_path_student, env_value, is_ironpython, is_linux, settings
from pyaedt.misc import list_installed_ansysem


class HierarchyDotNet:
    """Hierarchy."""

    def __getattr__(self, key):
        try:
            return super().__getattribute__(key)
        except AttributeError:
            try:
                return getattr(self._hierarchy, key)
            except AttributeError:
                raise AttributeError("Attribute not present")

    def __init__(self, app):
        self._app = app
        self.edb_api = self._app._edb
        self._hierarchy = self.edb_api.Cell.Hierarchy

    @property
    def api_class(self):  # pragma: no cover
        """Return Ansys.Ansoft.Edb class object."""
        return self._hierarchy

    @property
    def component(self):
        """Edb Dotnet Api Database `Edb.Cell.Hierarchy.Component`."""
        return self._hierarchy.Component

    @property
    def cell_instance(self):
        """Edb Dotnet Api Database `Edb.Cell.Hierarchy.CellInstance`."""
        return self._hierarchy.CellInstance

    @property
    def pin_group(self):
        """Edb Dotnet Api Database `Edb.Cell.Hierarchy.PinGroup`."""
        return self._hierarchy.PinGroup


class PolygonDataDotNet:  # pragma: no cover
    """Polygon Data."""

    def __getattr__(self, key):  # pragma: no cover
        try:
            return super().__getattribute__(key)
        except AttributeError:
            try:
                return getattr(self.dotnetobj, key)
            except AttributeError:
                raise AttributeError("Attribute not present")

    def __init__(self, pedb, api_object=None):
        self._pedb = pedb
        self.dotnetobj = pedb.edb_api.geometry.api_class.PolygonData
        self.edb_api = api_object

    @property
    def api_class(self):  # pragma: no cover
        """:class:`Ansys.Ansoft.Edb` class object."""
        return self.dotnetobj

    @property
    def arcs(self):  # pragma: no cover
        """List of Edb.Geometry.ArcData."""
        return list(self.edb_api.GetArcData())

    def get_points(self):
        """Get all points in polygon.

        Returns
        -------
        list[list[edb_value]]
        """
        return [[self._pedb.edb_value(i.X), self._pedb.edb_value(i.Y)] for i in list(self.edb_api.Points)]

    def add_point(self, x, y, incremental=False):
        """Add a point at the end of the point list of the polygon.

        Parameters
        ----------
        x: str, int, float
            X coordinate.
        y: str, in, float
            Y coordinate.
        incremental: bool
            Whether to add the point incrementally. The default value is ``False``. When
            ``True``, the coordinates of the added point are incremental to the last point.


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if incremental:
            x = self._pedb.edb_value(x)
            y = self._pedb.edb_value(y)
            last_point = self.get_points()[-1]
            x = "({})+({})".format(x, last_point[0].ToString())
            y = "({})+({})".format(y, last_point[1].ToString())
        return self.edb_api.AddPoint(GeometryDotNet(self._pedb).point_data(x, y))

    def get_bbox_of_boxes(self, points):
        """Get the EDB .NET API ``Edb.Geometry.GetBBoxOfBoxes`` database.

        Parameters
        ----------
        points : list or `Edb.Geometry.PointData`
        """
        if isinstance(points, list):
            points = convert_py_list_to_net_list(points)
        return self.dotnetobj.GetBBoxOfBoxes(points)

    def get_bbox_of_polygons(self, polygons):
        """Edb Dotnet Api Database `Edb.Geometry.GetBBoxOfPolygons`.

        Parameters
        ----------
        polygons : list or `Edb.Geometry.PolygonData`
        """
        if isinstance(polygons, list):
            polygons = convert_py_list_to_net_list(polygons)
        return self.dotnetobj.GetBBoxOfPolygons(polygons)

    def create_from_bbox(self, points):
        """Edb Dotnet Api Database `Edb.Geometry.CreateFromBBox`.

        Parameters
        ----------
        points : list or `Edb.Geometry.PointData`
        """
        from pyaedt.generic.clr_module import Tuple

        if isinstance(points, (tuple, list)):
            points = Tuple[self._pedb.edb_api.Geometry.PointData, self._pedb.edb_api.Geometry.PointData](
                points[0], points[1]
            )
        return self.dotnetobj.CreateFromBBox(points)

    def create_from_arcs(self, arcs, flag):
        """Edb Dotnet Api Database `Edb.Geometry.CreateFromArcs`.

        Parameters
        ----------
        arcs : list or `Edb.Geometry.ArcData`
            List of ArcData.
        flag : bool
        """
        if isinstance(arcs, list):
            arcs = convert_py_list_to_net_list(arcs)
        return self.dotnetobj.CreateFromArcs(arcs, flag)

    def unite(self, pdata):
        """Edb Dotnet Api Database `Edb.Geometry.Unite`.

        Parameters
        ----------
        pdata : list or `Edb.Geometry.PolygonData`
            Polygons to unite.

        """
        if isinstance(pdata, list):
            pdata = convert_py_list_to_net_list(pdata)
        return list(self.dotnetobj.Unite(pdata))

    def get_convex_hull_of_polygons(self, pdata):
        """Edb Dotnet Api Database `Edb.Geometry.GetConvexHullOfPolygons`.

        Parameters
        ----------
        pdata : list or List of `Edb.Geometry.PolygonData`
            Polygons to unite in a Convex Hull.
        """
        if isinstance(pdata, list):
            pdata = convert_py_list_to_net_list(pdata)
        return self.dotnetobj.GetConvexHullOfPolygons(pdata)


class NetDotNet:
    """Net Objects."""

    def __getattr__(self, key):
        try:
            return super().__getattribute__(key)
        except AttributeError:
            if self.net_obj and key in dir(self.net_obj):
                obj = self.net_obj
            else:
                obj = self.net
            try:
                return getattr(obj, key)
            except AttributeError:
                raise AttributeError("Attribute not present")

    def __init__(self, app, net_obj=None):
        self.net = app._edb.Cell.Net

        self.edb_api = app._edb
        self._app = app
        self.net_obj = net_obj

    @property
    def api_class(self):  # pragma: no cover
        """Return Ansys.Ansoft.Edb class object."""
        return self.net

    @property
    def api_object(self):
        """Return Ansys.Ansoft.Edb object."""
        return self.net_obj

    def find_by_name(self, layout, net):  # pragma: no cover
        """Edb Dotnet Api Database `Edb.Net.FindByName`."""
        return NetDotNet(self._app, self.net.FindByName(layout, net))

    def create(self, layout, name):
        """Edb Dotnet Api Database `Edb.Net.Create`."""
        return NetDotNet(self._app, self.net.Create(layout, name))

    def delete(self):
        """Edb Dotnet Api Database `Edb.Net.Delete`."""
        if self.net_obj:
            self.net_obj.Delete()
            self.net_obj = None

    @property
    def name(self):
        """Edb Dotnet Api Database `net.name` and  `Net.SetName()`."""
        if self.net_obj:
            return self.net_obj.GetName()

    @name.setter
    def name(self, value):
        if self.net_obj:
            self.net_obj.SetName(value)

    @property
    def is_null(self):
        """Edb Dotnet Api Database `Net.IsNull()`."""
        if self.net_obj:
            return self.net_obj.IsNull()

    @property
    def is_power_ground(self):
        """Edb Dotnet Api Database `Net.IsPowerGround()` and  `Net.SetIsPowerGround()`."""
        if self.net_obj:
            return self.net_obj.IsPowerGround()

    @property
    def _api_get_extended_net(self):
        """Extended net this net belongs to if it belongs to an extended net.
        If it does not belong to an extendednet, a null extended net is returned.
        """
        return self.net_obj.GetExtendedNet()

    @is_power_ground.setter
    def is_power_ground(self, value):
        if self.net_obj:
            self.net_obj.SetIsPowerGround(value)


class NetClassDotNet:
    """Net Class."""

    def __init__(self, app, api_object=None):
        self.cell_net_class = app._edb.Cell.NetClass
        self.api_object = api_object
        self.edb_api = app._edb
        self._app = app

    @property
    def api_nets(self):
        """Return Edb Nets object dictionary."""
        return {i.GetName(): i for i in list(self.api_object.Nets)}

    def api_create(self, name):
        """Edb Dotnet Api Database `Edb.NetClass.Create`."""
        return NetClassDotNet(self._app, self.cell_net_class.Create(self._app.active_layout, name))

    @property
    def name(self):
        """Edb Dotnet Api Database `NetClass.name` and  `NetClass.SetName()`."""
        if self.api_object:
            return self.api_object.GetName()

    @name.setter
    def name(self, value):
        if self.api_object:
            self.api_object.SetName(value)

    def add_net(self, name):
        """Add a new net.

        Parameters
        ----------
        name : str
            The name of the net to be added.

        Returns
        -------
        object
        """
        if self.api_object:
            edb_api_net = self.edb_api.Cell.Net.FindByName(self._app.active_layout, name)
            return self.api_object.AddNet(edb_api_net)

    def delete(self):  # pragma: no cover
        """Edb Dotnet Api Database `Delete`."""
        if self.api_object:
            self.api_object.Delete()
            self.api_object = None
            return not self.api_object

    @property
    def is_null(self):
        """Edb Dotnet Api Database `NetClass.IsNull()`."""
        if self.api_object:
            return self.api_object.IsNull()


class ExtendedNetDotNet(NetClassDotNet):
    """Extended net class."""

    def __init__(self, app, api_object=None):
        super().__init__(app, api_object)
        self.cell_extended_net = app._edb.Cell.ExtendedNet

    @property
    def api_class(self):  # pragma: no cover
        """Return Ansys.Ansoft.Edb class object."""
        return self.cell_extended_net

    def find_by_name(self, layout, net):  # pragma: no cover
        """Edb Dotnet Api Database `Edb.ExtendedNet.FindByName`."""
        return ExtendedNetDotNet(self._app, self.cell_extended_net.FindByName(layout, net))

    def api_create(self, name):
        """Edb Dotnet Api Database `Edb.ExtendedNet.Create`."""
        return ExtendedNetDotNet(self._app, self.cell_extended_net.Create(self._app.active_layout, name))


class DifferentialPairDotNet(NetClassDotNet):
    """Differential Pairs."""

    def __init__(self, app, api_object=None):
        super().__init__(app, api_object)
        self.cell_diff_pair = app._edb.Cell.DifferentialPair

    @property
    def api_class(self):  # pragma: no cover
        """Return Ansys.Ansoft.Edb class object."""
        return self.cell_diff_pair

    def find_by_name(self, layout, net):  # pragma: no cover
        """Edb Dotnet Api Database `Edb.DifferentialPair.FindByName`."""
        return DifferentialPairDotNet(self._app, self.cell_diff_pair.FindByName(layout, net))

    def api_create(self, name):
        """Edb Dotnet Api Database `Edb.DifferentialPair.Create`."""
        return DifferentialPairDotNet(self._app, self.cell_diff_pair.Create(self._app.active_layout, name))

    def _api_set_differential_pair(self, net_name_p, net_name_n):
        edb_api_net_p = self.edb_api.Cell.Net.FindByName(self._app.active_layout, net_name_p)
        edb_api_net_n = self.edb_api.Cell.Net.FindByName(self._app.active_layout, net_name_n)
        self.api_object.SetDifferentialPair(edb_api_net_p, edb_api_net_n)

    @property
    def api_positive_net(self):
        """Edb Api Positive net object."""
        if self.api_object:
            return self.api_object.GetPositiveNet()

    @property
    def api_negative_net(self):
        """Edb Api Negative net object."""
        if self.api_object:
            return self.api_object.GetNegativeNet()


class CellClassDotNet:
    """Cell Class."""

    def __getattr__(self, key):
        try:
            return super().__getattribute__(key)
        except AttributeError:
            try:
                return getattr(self._cell, key)
            except AttributeError:
                if self._active_cell and key in dir(self._active_cell):
                    try:
                        return getattr(self._active_cell, key)
                    except AttributeError:  # pragma: no cover
                        raise AttributeError("Attribute not present")
                else:
                    raise AttributeError("Attribute not present")

    def __init__(self, app, active_cell=None):
        self._app = app
        self.edb_api = app._edb
        self._cell = self.edb_api.Cell
        self._active_cell = active_cell

    @property
    def api_class(self):
        """Return Ansys.Ansoft.Edb class object."""
        return self._cell

    @property
    def api_object(self):
        """Return Ansys.Ansoft.Edb object."""
        return self._active_cell

    def create(self, db, cell_type, cell_name):
        return CellClassDotNet(self._app, self.cell.Create(db, cell_type, cell_name))

    @property
    def terminal(self):
        """Edb Dotnet Api Database `Edb.Cell.Terminal`."""
        return self._cell.Terminal

    @property
    def hierarchy(self):
        """Edb Dotnet Api Database `Edb.Cell.Hierarchy`.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.HierarchyDotNet`
        """
        return HierarchyDotNet(self._app)

    @property
    def cell(self):
        """Edb Dotnet Api Database `Edb.Cell`."""
        return self._cell.Cell

    @property
    def net(self):
        """Edb Dotnet Api Cell.Layer."""
        return NetDotNet(self._app)

    @property
    def layer_type(self):
        """Edb Dotnet Api Cell.LayerType."""
        return self._cell.LayerType

    @property
    def layer_type_set(self):
        """Edb Dotnet Api Cell.LayerTypeSet."""
        return self._cell.LayerTypeSet

    @property
    def layer(self):
        """Edb Dotnet Api Cell.Layer."""
        return self._cell.Layer

    @property
    def layout_object_type(self):
        """Edb Dotnet Api LayoutObjType."""
        return self._cell.LayoutObjType

    @property
    def primitive(self):
        """Edb Dotnet Api Database `Edb.Cell.Primitive`."""
        from pyaedt.edb_core.dotnet.primitive import PrimitiveDotNet

        return PrimitiveDotNet(self._app)


class UtilityDotNet:
    """Utility Edb class."""

    def __getattr__(self, key):
        try:
            return super().__getattribute__(key)
        except AttributeError:
            try:
                return getattr(self.utility, key)
            except AttributeError:
                raise AttributeError("Attribute not present")

    def __init__(self, app):
        self._app = app
        self.utility = app._edb.Utility
        self.edb_api = app._edb
        self.active_db = app._db
        self.active_cell = app._active_cell

    @property
    def api_class(self):
        """Return Ansys.Ansoft.Edb class object."""
        return self.utility

    def value(self, value, var_server=None):
        """Edb Dotnet Api Utility.Value."""
        if isinstance(value, self.utility.Value):
            return value
        if var_server:
            return self.utility.Value(value, var_server)
        if isinstance(value, (int, float)):
            return self.utility.Value(value)
        m1 = re.findall(r"(?<=[/+-/*//^/(/[])([a-z_A-Z/$]\w*)", str(value).replace(" ", ""))
        m2 = re.findall(r"^([a-z_A-Z/$]\w*)", str(value).replace(" ", ""))
        val_decomposed = list(set(m1).union(m2))
        if not val_decomposed:
            return self.utility.Value(value)
        var_server_db = self.active_db.GetVariableServer()
        var_names = var_server_db.GetAllVariableNames()
        var_server_cell = self.active_cell.GetVariableServer()
        var_names_cell = var_server_cell.GetAllVariableNames()
        if set(val_decomposed).intersection(var_names_cell):
            return self.utility.Value(value, var_server_cell)
        if set(val_decomposed).intersection(var_names):
            return self.utility.Value(value, var_server_db)
        return self.utility.Value(value)


class GeometryDotNet:
    """Geometry Edb Class."""

    def __getattr__(self, key):
        try:
            return super().__getattribute__(key)
        except AttributeError:
            try:
                return getattr(self.geometry, key)
            except AttributeError:  # pragma: no cover
                raise AttributeError("Attribute {} not present".format(key))

    def __init__(self, app):
        self._app = app
        self.geometry = self._app._edb.Geometry
        self.edb_api = self._app._edb

    @property
    def api_class(self):
        """Return Ansys.Ansoft.Edb class object."""
        return self.geometry

    @property
    def utility(self):
        return UtilityDotNet(self._app)

    def point_data(self, p1, p2):
        """Edb Dotnet Api Point."""
        if isinstance(p1, (int, float, str, list)):
            p1 = self.utility.value(p1)
        if isinstance(p2, (int, float, str, list)):
            p2 = self.utility.value(p2)
        return self.geometry.PointData(p1, p2)

    def point3d_data(self, p1, p2, p3):
        """Edb Dotnet Api Point 3D."""
        if isinstance(p1, (int, float, str, list)):
            p1 = self.utility.value(p1)
        if isinstance(p2, (int, float, str, list)):
            p2 = self.utility.value(p2)
        if isinstance(p3, (int, float, str, list)):
            p3 = self.utility.value(p3)
        return self.geometry.Point3DData(p1, p2, p3)

    @property
    def extent_type(self):
        """Edb Dotnet Api Extent Type."""
        return self.geometry.ExtentType

    @property
    def polygon_data(self):
        """Polygon Data.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.PolygonDataDotNet`
        """
        return PolygonDataDotNet(self._app)

    def arc_data(self, point1, point2, rotation=None, center=None, height=None):
        """Compute EBD arc data.

        Parameters
        ----------
        point1 : list or PointData object
        point2 : list or PointData object
        rotation : int or RotationDir enumerator
        center :  list or PointData object
        height : float

        Returns
        -------
        Edb ArcData object
        """
        if isinstance(point1, (list, tuple)):
            point1 = self.point_data(point1[0], point1[1])
        if isinstance(point2, (list, tuple)):
            point2 = self.point_data(point2[0], point2[1])
        if center and isinstance(center, (list, tuple)):
            center = self.point_data(center[0], center[1])
        if rotation and center:
            return self.geometry.ArcData(point1, point2, rotation, center)
        elif height:
            return self.geometry.ArcData(point1, point2, height)
        else:
            return self.geometry.ArcData(point1, point2)


class CellDotNet:
    """Cell Dot net."""

    def __getattr__(self, key):
        try:
            return super().__getattribute__(key)
        except AttributeError:
            try:
                return getattr(self.edb_api, key)
            except AttributeError:
                raise AttributeError("Attribute not present")

    def __init__(self, app):
        self._app = app
        self.edb_api = app._edb

    @property
    def api_class(self):
        """Return Ansys.Ansoft.Edb class object."""
        return self.edb_api

    @property
    def definition(self):
        """Edb Dotnet Api Definition."""
        return self.edb_api.Definition

    @property
    def database(self):
        """Edb Dotnet Api Database."""
        return self.edb_api.Database

    @property
    def cell(self):
        """Edb Dotnet Api Database `Edb.Cell`.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.database.CellClassDotNet`
        """
        return CellClassDotNet(self._app)

    @property
    def utility(self):
        """Utility class.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.database.UtilityDotNet`
        """
        return UtilityDotNet(self._app)

    @property
    def geometry(self):
        """Geometry class.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.database.GeometryDotNet`
        """
        return GeometryDotNet(self._app)


class EdbDotNet(object):
    """Edb Dot Net Class."""

    def __init__(self, edbversion, student_version=False):
        self._global_logger = pyaedt_logger
        self._logger = pyaedt_logger
        if not edbversion:  # pragma: no cover
            try:
                edbversion = "20{}.{}".format(list_installed_ansysem()[0][-3:-1], list_installed_ansysem()[0][-1:])
                self._logger.info("Edb version " + edbversion)
            except IndexError:
                raise Exception("No ANSYSEM_ROOTxxx is found.")
        self.edbversion = edbversion
        self.student_version = student_version
        """Initialize DLLs."""
        from pyaedt.generic.clr_module import _clr, edb_initialized

        if settings.enable_screen_logs:
            self.logger.enable_stdout_log()
        else:  # pragma: no cover
            self.logger.disable_stdout_log()
        if not edb_initialized:  # pragma: no cover
            self.logger.error("Failed to initialize Dlls.")
            return
        self.logger.info("Logger is initialized in EDB.")
        self.logger.info("pyaedt v%s", __version__)
        self.logger.info("Python version %s", sys.version)
        if is_linux:  # pragma: no cover
            if env_value(self.edbversion) in os.environ or settings.edb_dll_path:
                if settings.edb_dll_path:
                    self.base_path = settings.edb_dll_path
                else:
                    self.base_path = env_path(self.edbversion)
                sys.path.append(self.base_path)
            else:
                main = sys.modules["__main__"]
                if "oDesktop" in dir(main):
                    self.base_path = main.oDesktop.GetExeDir()
                    sys.path.append(main.oDesktop.GetExeDir())
                    os.environ[env_value(self.edbversion)] = self.base_path
                else:
                    edb_path = os.getenv("PYAEDT_SERVER_AEDT_PATH")
                    if edb_path:
                        self.base_path = edb_path
                        sys.path.append(edb_path)
                        os.environ[env_value(self.edbversion)] = self.base_path
            if is_ironpython:
                _clr.AddReferenceToFile("Ansys.Ansoft.Edb.dll")
                _clr.AddReferenceToFile("Ansys.Ansoft.EdbBuilderUtils.dll")
                _clr.AddReferenceToFileAndPath(os.path.join(self.base_path, "Ansys.Ansoft.SimSetupData.dll"))
            else:
                _clr.AddReference("Ansys.Ansoft.Edb")
                _clr.AddReference("Ansys.Ansoft.EdbBuilderUtils")
                _clr.AddReference("Ansys.Ansoft.SimSetupData")
        else:
            if settings.edb_dll_path:
                self.base_path = settings.edb_dll_path
            elif self.student_version:
                self.base_path = env_path_student(self.edbversion)
            else:
                self.base_path = env_path(self.edbversion)
            sys.path.append(self.base_path)
            _clr.AddReference("Ansys.Ansoft.Edb")
            _clr.AddReference("Ansys.Ansoft.EdbBuilderUtils")
            _clr.AddReference("Ansys.Ansoft.SimSetupData")
        os.environ["ECAD_TRANSLATORS_INSTALL_DIR"] = self.base_path
        oaDirectory = os.path.join(self.base_path, "common", "oa")
        os.environ["ANSYS_OADIR"] = oaDirectory
        os.environ["PATH"] = "{};{}".format(os.environ["PATH"], self.base_path)
        edb = __import__("Ansys.Ansoft.Edb")
        self._edb = edb.Ansoft.Edb
        edbbuilder = __import__("Ansys.Ansoft.EdbBuilderUtils")
        self.edbutils = edbbuilder.Ansoft.EdbBuilderUtils
        self.simSetup = __import__("Ansys.Ansoft.SimSetupData")
        self.simsetupdata = self.simSetup.Ansoft.SimSetupData.Data

    @property
    def student_version(self):
        """Set the student version flag."""
        return self._student_version

    @student_version.setter
    def student_version(self, value):
        self._student_version = value

    @property
    def logger(self):
        """Logger for EDB.

        Returns
        -------
        :class:`pyaedt.aedt_logger.AedtLogger`
        """
        return self._logger

    @property
    def edb_api(self):
        """Edb Dotnet Api class.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.database.CellDotNet`
        """
        return CellDotNet(self)

    @property
    def database(self):
        """Edb Dotnet Api Database."""
        return self.edb_api.database

    @property
    def definition(self):
        """Edb Dotnet Api Database `Edb.Definition`."""
        return self.edb_api.Definition


class Database(EdbDotNet):
    """Class representing a database object."""

    def __init__(self, edbversion, student_version=False):
        """Initialize a new Database."""
        EdbDotNet.__init__(self, edbversion=edbversion, student_version=student_version)
        self._db = None

    @property
    def api_class(self):
        """Return Ansys.Ansoft.Edb class object."""
        return self._edb

    @property
    def api_object(self):
        """Return Ansys.Ansoft.Edb object."""
        return self._db

    @property
    def db(self):
        """Active database object."""
        return self._db

    def run_as_standalone(self, flag):
        """Set if Edb is run as standalone or embedded in AEDT.

        Parameters
        ----------
        flag : bool
            Whether if Edb is run as standalone or embedded in AEDT.
        """
        self.edb_api.database.SetRunAsStandAlone(flag)

    def create(self, db_path):
        """Create a Database at the specified file location.

        Parameters
        ----------
        db_path : str
            Path to top-level database folder

        Returns
        -------
        Database
        """
        self._db = self.edb_api.database.Create(db_path)
        return self._db

    def open(self, db_path, read_only):
        """Open an existing Database at the specified file location.

        Parameters
        ----------
        db_path : str
            Path to top-level Database folder.
        read_only : bool
            Obtain read-only access.

        Returns
        -------
        Database or None
            The opened Database object, or None if not found.
        """
        self._db = self.edb_api.database.Open(
            db_path,
            read_only,
        )
        return self._db

    def delete(self, db_path):
        """Delete a database at the specified file location.

        Parameters
        ----------
        db_path : str
            Path to top-level database folder.
        """
        return self.edb_api.database.Delete(db_path)

    def save(self):
        """Save any changes into a file."""
        return self._db.Save()

    def close(self):
        """Close the database.

        .. note::
            Unsaved changes will be lost.
        """
        return self._db.Close()

    @property
    def top_circuit_cells(self):
        """Get top circuit cells.

        Returns
        -------
        list[:class:`Cell <ansys.edb.layout.Cell>`]
        """
        return [CellClassDotNet(self, i) for i in list(self._db.TopCircuitCells)]

    @property
    def circuit_cells(self):
        """Get all circuit cells in the Database.

        Returns
        -------
        list[:class:`Cell <ansys.edb.layout.Cell>`]
        """
        return [CellClassDotNet(self, i) for i in list(self._db.CircuitCells)]

    @property
    def footprint_cells(self):
        """Get all footprint cells in the Database.

        Returns
        -------
        list[:class:`Cell <ansys.edb.layout.Cell>`]
        """
        return [CellClassDotNet(self, i) for i in list(self._db.FootprintCells)]

    @property
    def edb_uid(self):
        """Get ID of the database.

        Returns
        -------
        int
            The unique EDB id of the Database.
        """
        return self._db.GetId()

    @property
    def is_read_only(self):
        """Determine if the database is open in a read-only mode.

        Returns
        -------
        bool
            True if Database is open with read only access, otherwise False.
        """
        return self._db.IsReadOnly()

    def find_by_id(self, db_id):
        """Find a database by ID.

        Parameters
        ----------
        db_id : int
            The Database's unique EDB id.

        Returns
        -------
        Database
            The Database or Null on failure.
        """
        self.edb_api.database.FindById(db_id)

    def save_as(self, path, version=""):
        """Save this Database to a new location and older EDB version.

        Parameters
        ----------
        path : str
            New Database file location.
        version : str
            EDB version to save to. Empty string means current version.
        """
        self._db.SaveAs(path, version)

    @property
    def directory(self):
        """Get the directory of the Database.

        Returns
        -------
        str
            Directory of the Database.
        """
        return self._db.GetDirectory()

    def get_product_property(self, prod_id, attr_it):
        """Get the product-specific property value.

        Parameters
        ----------
        prod_id : ProductIdType
            Product ID.
        attr_it : int
            Attribute ID.

        Returns
        -------
        str
            Property value returned.
        """
        return self._db.GetProductProperty(prod_id, attr_it)

    def set_product_property(self, prod_id, attr_it, prop_value):
        """Set the product property associated with the given product and attribute ids.

        Parameters
        ----------
        prod_id : ProductIdType
            Product ID.
        attr_it : int
            Attribute ID.
        prop_value : str
            Product property's new value
        """
        self._db.SetProductProperty(prod_id, attr_it, prop_value)

    def get_product_property_ids(self, prod_id):
        """Get a list of attribute ids corresponding to a product property id.

        Parameters
        ----------
        prod_id : ProductIdType
            Product ID.

        Returns
        -------
        list[int]
            The attribute ids associated with this product property.
        """
        return self._db.GetProductPropertyIds(prod_id)

    def import_material_from_control_file(self, control_file, schema_dir=None, append=True):
        """Import materials from the provided control file.

        Parameters
        ----------
        control_file : str
            Control file name with full path.
        schema_dir : str
            Schema file path.
        append : bool
            True if the existing materials in Database are kept. False to remove existing materials in database.
        """
        self._db.ImportMaterialFromControlFile(
            control_file,
            schema_dir,
            append,
        )

    @property
    def version(self):
        """Get version of the Database.

        Returns
        -------
        tuple(int, int)
            A tuple of the version numbers [major, minor]
        """
        major, minor = self._db.GetVersion()
        return major, minor

    def scale(self, scale_factor):
        """Uniformly scale all geometry and their locations by a positive factor.

        Parameters
        ----------
        scale_factor : float
            Amount that coordinates are multiplied by.
        """
        return self._db.Scale(scale_factor)

    @property
    def source(self):
        """Get source name for this Database.

        This attribute is also used to set the source name.

        Returns
        -------
        str
            name of the source
        """
        return self._db.GetSource()

    @source.setter
    def source(self, source):
        """Set source name of the database."""
        self._db.SetSource(source)

    @property
    def source_version(self):
        """Get the source version for this Database.

        This attribute is also used to set the version.

        Returns
        -------
        str
            version string

        """
        return self._db.GetSourceVersion()

    @source_version.setter
    def source_version(self, source_version):
        """Set source version of the database."""
        self._db.SetSourceVersion(source_version)

    def copy_cells(self, cells_to_copy):
        """Copy Cells from other Databases or this Database into this Database.

        Parameters
        ----------
        cells_to_copy : list[:class:`Cell <ansys.edb.layout.Cell>`]
            Cells to copy.

        Returns
        -------
        list[:class:`Cell <ansys.edb.layout.Cell>`]
            New Cells created in this Database.
        """
        if not isinstance(cells_to_copy, list):
            cells_to_copy = [cells_to_copy]
        _dbCells = convert_py_list_to_net_list(cells_to_copy)
        return self._db.CopyCells(_dbCells)

    @property
    def apd_bondwire_defs(self):
        """Get all APD bondwire definitions in this Database.

        Returns
        -------
        list[:class:`ApdBondwireDef <ansys.edb.definition.ApdBondwireDef>`]
        """
        return list(self._db.APDBondwireDefs)

    @property
    def jedec4_bondwire_defs(self):
        """Get all JEDEC4 bondwire definitions in this Database.

        Returns
        -------
        list[:class:`Jedec4BondwireDef <ansys.edb.definition.Jedec4BondwireDef>`]
        """
        return list(self._db.Jedec4BondwireDefs)

    @property
    def jedec5_bondwire_defs(self):
        """Get all JEDEC5 bondwire definitions in this Database.

        Returns
        -------
        list[:class:`Jedec5BondwireDef <ansys.edb.definition.Jedec5BondwireDef>`]
        """
        return list(self._db.Jedec5BondwireDefs)

    @property
    def padstack_defs(self):
        """Get all Padstack definitions in this Database.

        Returns
        -------
        list[:class:`PadstackDef <ansys.edb.definition.PadstackDef>`]
        """
        return list(self._db.PadstackDefs)

    @property
    def package_defs(self):
        """Get all Package definitions in this Database.

        Returns
        -------
        list[:class:`PackageDef <ansys.edb.definition.PackageDef>`]
        """
        return list(self._db.PackageDefs)

    @property
    def component_defs(self):
        """Get all component definitions in the database.

        Returns
        -------
        list[:class:`ComponentDef <ansys.edb.definition.ComponentDef>`]
        """
        return list(self._db.ComponentDefs)

    @property
    def material_defs(self):
        """Get all material definitions in the database.

        Returns
        -------
        list[:class:`MaterialDef <ansys.edb.definition.MaterialDef>`]
        """
        return list(self._db.MaterialDefs)

    @property
    def dataset_defs(self):
        """Get all dataset definitions in the database.

        Returns
        -------
        list[:class:`DatasetDef <ansys.edb.definition.DatasetDef>`]
        """
        return list(self._db.DatasetDefs)

    def attach(self, hdb):  # pragma no cover
        """Attach the database to existing AEDT instance.

        Parameters
        ----------
        hdb

        Returns
        -------

        """
        from pyaedt.generic.clr_module import Convert

        hdl = Convert.ToUInt64(hdb)
        self._db = self.edb_api.database.Attach(hdl)
        return self._db
