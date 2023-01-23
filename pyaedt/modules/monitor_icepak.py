import re

from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import pyaedt_function_handler


class Monitor:
    """Provides Icepak monitor methods."""

    def __init__(self, p_app):
        self._face_monitors = {}
        self._point_monitors = {}
        self._app = p_app
        self._omonitor = self._app.odesign.GetModule("Monitor")
        if self._app.design_properties:  # if is not a 3d comp/blank file
            aedtfile_monitor_dict = self._app.design_properties["Monitor"]["IcepakMonitors"].copy()
            del aedtfile_monitor_dict["NextUniqueID"]
            del aedtfile_monitor_dict["MoveBackwards"]
            if aedtfile_monitor_dict:
                self._load_monitor_objects(aedtfile_monitor_dict)

    @pyaedt_function_handler
    def _find_point(self, position):
        for point in self._app.oeditor.GetPoints():
            point_pos = self._app.oeditor.GetChildObject(point).GetPropValue("Position")
            if all(point_pos[2 * i + 1] == position[i] for i in range(3)):
                return point
        return None

    @pyaedt_function_handler
    def _generate_monitor_names(self, name, n):
        """Create list of names for monitor objects following Icepak naming rules.

        Parameters
        ----------
        name : str
            Name for the first monitor object
        n : int
            Number of names to be generated

        Returns
        -------
        list
            List of names
        """
        if n == 1 and name not in self.all_monitors:
            return [name]
        else:
            if name not in self.all_monitors:
                names = [name]
            else:
                names = []
                n += 1
            j = 1
            if re.search(r"\d+$", name) is not None:
                j = int(re.search(r"\d+$", name).group(0)) + 1
            n_names_left = n - 1
            while n_names_left:
                i = n - 1 - n_names_left
                candidate_name = re.sub(r"\d+$", "", name) + str(i + j)
                if candidate_name not in self.all_monitors:
                    names.append(candidate_name)
                    n_names_left -= 1
                n += 1
            return names

    @pyaedt_function_handler
    def _load_monitor_objects(self, aedtfile_monitor_dict):
        quantities_dict = {  # pragma: no cover
            8: "Speed",
            9: "Pressure",
            10: "TKE",
            11: "Epsilon",
            12: "ViscosityRatio",
            16: "MassFlow",
            17: "VolumeFlow",
            18: "WallYPlus",
            19: "Temperature",
            20: "K_X",
            21: "K_Y",
            22: "K_Z",
            29: "HeatFlux",
            31: "HeatFlowRate",
        }
        for monitor_name, monitor_prop in aedtfile_monitor_dict.items():
            if "Faces" in monitor_prop.keys():
                self._face_monitors[monitor_name] = FaceMonitor(
                    monitor_name,
                    "Face",
                    monitor_prop["Faces"][0],
                    [quantities_dict[i] for i in monitor_prop["Quantities"]],
                    self._app,
                )
            elif "Objects" in monitor_prop.keys() and monitor_prop["Type"] == 2:
                self._point_monitors[monitor_name] = PointMonitor(
                    monitor_name,
                    "Object",
                    self._app.oeditor.GetObjectNameByID(int(monitor_prop["Objects"][0])),
                    [quantities_dict[i] for i in monitor_prop["Quantities"]],
                    self._app,
                )
            elif "Objects" in monitor_prop.keys():
                self._face_monitors[monitor_name] = FaceMonitor(
                    monitor_name,
                    "Surface",
                    self._app.oeditor.GetObjectNameByID(int(monitor_prop["Objects"][0])),
                    [quantities_dict[i] for i in monitor_prop["Quantities"]],
                    self._app,
                )
            elif "Points" in monitor_prop.keys():
                point_name = self._find_point(
                    self._app.odesign.GetChildObject("Monitor")
                    .GetChildObject(monitor_name)
                    .GetPropValue("Location")
                    .split(", ")
                )
                self._point_monitors[monitor_name] = PointMonitor(
                    monitor_name,
                    "Point",
                    point_name,
                    [quantities_dict[i] for i in monitor_prop["Quantities"]],
                    self._app,
                )
            else:
                self._point_monitors[monitor_name] = PointMonitor(
                    monitor_name,
                    "Vertex",
                    monitor_prop["Vertices"][0],
                    [quantities_dict[i] for i in monitor_prop["Quantities"]],
                    self._app,
                )
        return True

    @pyaedt_function_handler
    def get_icepak_monitor_object(self, monitor_name):
        """Get Icepak monitor object.

        Returns
        -------
        oEditor COM Object
        """
        return self._app.odesign.GetChildObject("Monitor").GetChildObject(monitor_name)

    @property
    def face_monitors(self):
        """Get face monitor objects.

        Returns
        -------
        dict
            Face monitor objects dictionary.

        """
        return self._face_monitors

    @property
    def point_monitors(self):
        """Get face monitor objects.

        Returns
        -------
        dict
            Point monitor objects dictionary.

        """
        return self._point_monitors

    @property
    def all_monitors(self):
        """Get all monitor objects.

        Returns
        -------
        dict
            Monitor objects dictionary.

        """
        out_dict = {}
        out_dict.update(self.face_monitors)
        out_dict.update(self.point_monitors)
        return out_dict

    @pyaedt_function_handler()
    def assign_point_monitor(self, point_position, monitor_quantity="Temperature", monitor_name=None):
        """Create and assign a point monitor.

        Parameters
        ----------
        point_position : list
            List of the ``[x, y, z]`` coordinates for the point or list of list of coordinates.
        monitor_quantity : str or list, optional
            Quantity being monitored.  The default is ``"Temperature"``.
        monitor_name : str, optional
            Name of the monitor. The default is ``None``, in which case
            the name is randomly generated.

        Returns
        -------
        str or list
            Monitor name or list of monitor names when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AssignPointMonitor

        Examples
        --------
        Create two temperature monitor at the points ``[0, 0, 0]`` and ``[1, 1, 1]``.

        >>> icepak.monitor.assign_point_monitor([[0,0,0], [1, 1, 1]], monitor_name="monitor1")
        ['monitor1', 'monitor2']

        """
        point_names = []
        if not isinstance(point_position[0], list):
            point_position = [point_position]
        if not isinstance(monitor_quantity, list):
            monitor_quantity = [monitor_quantity]
        for p_p in point_position:
            point_name = generate_unique_name("Point")
            self._app.modeler.oeditor.CreatePoint(
                [
                    "NAME:PointParameters",
                    "PointX:=",
                    self._app.modeler._arg_with_dim(p_p[0]),
                    "PointY:=",
                    self._app.modeler._arg_with_dim(p_p[1]),
                    "PointZ:=",
                    self._app.modeler._arg_with_dim(p_p[2]),
                ],
                ["NAME:Attributes", "Name:=", point_name, "Color:=", "(143 175 143)"],
            )
            point_names.append(point_name)
        if not monitor_name:
            monitor_name = generate_unique_name("Monitor")
        self._omonitor.AssignPointMonitor(
            ["NAME:" + monitor_name, "Quantities:=", monitor_quantity, "Points:=", point_names]
        )
        try:
            monitor_names = self._generate_monitor_names(monitor_name, len(point_position))
            for i, mn in enumerate(monitor_names):
                self._point_monitors[mn] = PointMonitor(mn, "Point", point_names[i], monitor_quantity, self._app)
        except:  # pragma: no cover
            return False
        if len(monitor_names) == 1:
            return monitor_names[0]
        else:
            return monitor_names

    @pyaedt_function_handler()
    def assign_point_monitor_to_vertex(self, vertex_id, monitor_quantity="Temperature", monitor_name=None):
        """Create and assign a point monitor to a vertex.

        Parameters
        ----------
        vertex_id : int or list
            ID of the vertex or list of IDs.
        monitor_quantity : str or list, optional
            Quantity being monitored.  The default is ``"Temperature"``.
        monitor_name : str, optional
            Name of the monitor. The default is ``None``, in which case
            the name is randomly generated.

        Returns
        -------
        str or list
            Monitor name or list of monitor names when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.AssignPointMonitor

        """
        if isinstance(vertex_id, int):
            vertex_id = [vertex_id]
        if isinstance(monitor_quantity, str):
            monitor_quantity = [monitor_quantity]
        if not monitor_name:
            monitor_name = generate_unique_name("Monitor")
        self._omonitor.AssignPointMonitor(
            ["NAME:" + monitor_name, "Quantities:=", monitor_quantity, "Vertices:=", vertex_id]
        )
        try:
            monitor_names = self._generate_monitor_names(monitor_name, len(vertex_id))
            for i, mn in enumerate(monitor_names):
                self._point_monitors[mn] = PointMonitor(mn, "Vertex", vertex_id[i], monitor_quantity, self._app)
        except:  # pragma: no cover
            return False
        if len(monitor_names) == 1:
            return monitor_names[0]
        else:
            return monitor_names

    @pyaedt_function_handler()
    def assign_surface_monitor(self, surface_name, monitor_quantity="Temperature", monitor_name=None):
        """Assign a surface monitor.

        Parameters
        ----------
        surface_name : str or list
            Name of the surface or list of names.
        monitor_quantity : str or list, optional
            Quantity being monitored.  The default is ``"Temperature"``.
        monitor_name : str, optional
            Name of the monitor. The default is ``None``, in which case
            the name is randomly generated.

        Returns
        -------
        str or list
            Monitor name or list of monitor names when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.AssignFaceMonitor

        Examples
        --------

        Create a rectangle named ``"Surface1"`` and assign a temperature monitor to that surface.

        >>> surface = icepak.modeler.create_rectangle(icepak.PLANE.XY,
        ...                                           [0, 0, 0], [10, 20], name="Surface1")
        >>> icepak.assign_surface_monitor("Surface1", monitor_name="monitor")
        'monitor'
        """
        if isinstance(surface_name, str):
            surface_name = [surface_name]
        if isinstance(monitor_quantity, str):
            monitor_quantity = [monitor_quantity]
        if not monitor_name:
            monitor_name = generate_unique_name("Monitor")
        self._omonitor.AssignFaceMonitor(
            ["NAME:" + monitor_name, "Quantities:=", monitor_quantity, "Objects:=", surface_name]
        )
        try:
            monitor_names = self._generate_monitor_names(monitor_name, len(surface_name))
            for i, mn in enumerate(monitor_names):
                self._face_monitors[mn] = FaceMonitor(mn, "Surface", surface_name[i], monitor_quantity, self._app)
        except:  # pragma: no cover
            return False
        if len(monitor_names) == 1:
            return monitor_names[0]
        else:
            return monitor_names

    @pyaedt_function_handler()
    def assign_face_monitor(self, face_id, monitor_quantity="Temperature", monitor_name=None):
        """Assign a face monitor.

        Parameters
        ----------
        face_id : int or list
            Face id or list of ids
        monitor_quantity : str or list, optional
            Quantity being monitored.  The default is ``"Temperature"``.
        monitor_name : str, optional
            Name of the monitor. The default is ``None``, in which case
            the name is randomly generated.

        Returns
        -------
        str or list
            Monitor name or list of monitor names when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.AssignFaceMonitor
        """
        if isinstance(face_id, int):
            face_id = [face_id]
        if isinstance(monitor_quantity, str):
            monitor_quantity = [monitor_quantity]
        if not monitor_name:
            monitor_name = generate_unique_name("Monitor")
        self._omonitor.AssignFaceMonitor(["NAME:" + monitor_name, "Quantities:=", monitor_quantity, "Faces:=", face_id])
        try:
            monitor_names = self._generate_monitor_names(monitor_name, len(face_id))
            for i, mn in enumerate(monitor_names):
                self._face_monitors[mn] = FaceMonitor(mn, "Face", face_id[i], monitor_quantity, self._app)
        except:  # pragma: no cover
            return False
        if len(monitor_names) == 1:
            return monitor_names[0]
        else:
            return monitor_names

    @pyaedt_function_handler()
    def assign_point_monitor_in_object(self, name, monitor_quantity="Temperature", monitor_name=None):
        """Assign a point monitor in the centroid of a specific object.

        Parameters
        ----------
        name : str or list
            Name of the object to assign monitor point to.
        monitor_quantity : str or list, optional
            Quantity being monitored.  The default is ``"Temperature"``.
        monitor_name : str, optional
            Name of the monitor. The default is ``None``, in which case
            the name is randomly generated.

        Returns
        -------
        str or list
            Monitor name or list of names when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.AssignPointMonitor

        Examples
        --------

        Create a box named ``"BlockBox1"`` and assign a temperature monitor point to that object.

        >>> box = icepak.modeler.create_box([1, 1, 1], [3, 3, 3], "BlockBox1", "copper")
        >>> icepak.assign_point_monitor(box.name, monitor_name="monitor2")
        "'monitor2'
        """
        if not isinstance(name, list):
            name = [name]
        if not isinstance(monitor_quantity, list):
            monitor_quantity = [monitor_quantity]
        name_sel = self._app.modeler.convert_to_selections(name, True)
        original_monitors = list(self._app.odesign.GetChildObject("Monitor").GetChildNames())
        if not monitor_name:
            monitor_name = generate_unique_name("Monitor")
        elif monitor_name in original_monitors:
            monitor_name = generate_unique_name(monitor_name)
        existing_names = list(set(name_sel).intersection(self._app.modeler.object_names))
        if existing_names:
            self._omonitor.AssignPointMonitor(
                ["NAME:" + monitor_name, "Quantities:=", monitor_quantity, "Objects:=", existing_names]
            )
        else:
            self._app.logger.error("Object is not present in the design")
            return False
        try:
            monitor_names = self._generate_monitor_names(monitor_name, len(existing_names))
            for i, mn in enumerate(monitor_names):
                self._point_monitors[mn] = PointMonitor(mn, "Object", existing_names[i], monitor_quantity, self._app)
        except:  # pragma: no cover
            return False
        if len(monitor_names) == 1:
            return monitor_names[0]
        else:
            return monitor_names

    @pyaedt_function_handler()
    def delete_monitor(self, monitor_name):
        """Delete monitor object.

        Parameters
        ----------
        monitor_name : str
            Name of the monitor object to delete

        Returns
        -------
        bool
            ``False`` if succesflul, else ``False``.

        References
        ----------

        >>> oModule.DeleteMonitors

        """
        try:
            self._omonitor.DeleteMonitors([monitor_name])
            try:
                del self._face_monitors[monitor_name]
            except KeyError:
                del self._point_monitors[monitor_name]
            return True
        except:
            return False

    @pyaedt_function_handler()
    def get_monitor_object_assignment(self, monitor):
        """
        Get the object that the monitor is applied to.

        Parameters
        ----------
        monitor : str or FaceMonitor or PointMonitor object
           Monitor object or monitor object name.

        Returns
        -------
        str
            Name of the object.
        """
        if isinstance(monitor, str):
            monitor = self.all_monitors[monitor]
        m_type = monitor.type
        if m_type == "Face":
            return self._app.oeditor.GetObjectNameByFaceID(monitor.id)
        elif m_type == "Vertex":
            return self._app.oeditor.GetObjectNameByVertexID(monitor.id)
        else:
            return monitor.id

    def _delete_removed_monitors(self):
        existing_monitors = self._app.odesign.GetChildObject("Monitor").GetChildNames()
        for j in [self._face_monitors, self._point_monitors]:
            for i in list(j):
                if i not in existing_monitors:
                    del j[i]
                    self._app.logger.info(
                        i + " monitor object lost its assignment due to geometry modifications and has been deleted."
                    )

    @pyaedt_function_handler()
    def insert_monitor_object_from_dict(self, monitor_dict, mode=0):
        """Insert a monitor.

        Parameters
        ----------
        monitor_dict : dict
           Dictionary containing monitor object information.
        mode : int
            Integer to select the information to handle. To identify the faces, vertices,
            surfaces, and object to which to assign the monitor to, you can use:
            - ids and names, mode=0, required dict keys: "Name", "Type", "ID", "Quantity".
            - positions, mode=1, required dict keys: "Name", "Type", "Geometry Assignment", "Location", "Quantity".

        Returns
        -------
        str
            Name of the monitor object.
        """
        m_case = monitor_dict["Type"]
        m_quantity = monitor_dict["Quantity"]
        m_name = monitor_dict["Name"]
        m_object = None
        if mode == 1:
            if m_case == "Face":
                for f in self._app.modeler.get_object_from_name(monitor_dict["Geometry Assignment"]).faces:
                    if f.center == monitor_dict["Location"]:
                        m_object = f.id
                        break
            elif m_case == "Vertex":
                for v in self._app.modeler.get_object_from_name(monitor_dict["Geometry Assignment"]).vertices:
                    if v.position == monitor_dict["Location"]:
                        m_object = v.id
                        break
            elif m_case == "Object":
                m_object = monitor_dict["Geometry Assignment"]
            elif m_case == "Surface":
                m_object = monitor_dict["Geometry Assignment"]
        elif mode == 0:
            m_object = monitor_dict["ID"]
        else:
            self._app.logger.error("Only modes supported are 0 and 1")
        if m_object is None:
            self._app.logger.error("{} monitor object could not be restored".format(m_name))
            return False
        self._app.configurations.update_monitor(m_case, m_object, m_quantity, m_name)
        return m_name


class ObjectMonitor:
    """Provides Icepak Monitor methods and properties."""

    def __init__(self, monitor_name, monitor_type, monitor_id, quantity, app):
        self._name = monitor_name
        self._type = monitor_type
        self._id = monitor_id
        self._quantities = quantity
        self._app = app

    @property
    def geometry_assignment(self):
        """
        Get the geometry assignment for the monitor object.

        Returns
        -------
        str
        """
        return self._app.monitor.get_monitor_object_assignment(self)

    @property
    def name(self):
        """
        Get the name of the monitor object.

        Returns
        -------
        str
        """
        return self._name

    @property
    def id(self):
        """
        Get the name, or id of geometry assignment.

        Returns
        -------
        str or int
        """
        return self._id

    @property
    def properties(self):
        """
        Get a dictionary of properties.

        Returns
        -------
        dict
        """
        return {
            "Name": self.name,
            "Object": self._app.odesign.GetChildObject("Monitor").GetChildObject(self.name),
            "Type": self.type,
            "ID": self.id,
            "Location": self.location,
            "Quantity": self.quantities,
            "Geometry Assignment": self.geometry_assignment,
        }

    @pyaedt_function_handler
    def delete(self):
        """
        Delete a monitor object.

        Returns
        -------
        bool
            ``True`` if successful.
        """
        self._app.monitor.delete_monitor(self.name)
        return True

    @property
    def quantities(self):
        """
        Get the quantities being monitored.

        Returns
        -------
        list
        """
        return self._quantities

    @property
    def type(self):
        """
        Get the monitor type.

        Returns
        -------
        str
        """
        return self._type


class PointMonitor(ObjectMonitor):
    """Provides Icepak point monitor methods and properties."""

    def __init__(self, monitor_name, monitor_type, point_id, quantity, app):
        ObjectMonitor.__init__(self, monitor_name, monitor_type, point_id, quantity, app)

    @property
    def location(self):
        """
        Get the monitor point location.

        Returns
        -------
        list
            List of floats containing [x, y, z] position.
        """
        return [
            float(i.strip(self._app.modeler.model_units))
            for i in self._app.odesign.GetChildObject("Monitor")
            .GetChildObject(self._name)
            .GetPropValue("Location")
            .split(", ")
        ]


class FaceMonitor(ObjectMonitor):
    """Provides Icepak face monitor properties and methods."""

    def __init__(self, monitor_name, monitor_type, face_id, quantity, app):
        ObjectMonitor.__init__(self, monitor_name, monitor_type, face_id, quantity, app)

    @property
    def location(self):
        """
        Get the monitor location in terms of face or surface center.

        Returns
        -------
        list
            List of floats containing [x, y, z] position.
        """
        if self.type == "Face":
            for f in self._app.modeler.get_object_from_name(self.geometry_assignment).faces:
                if f.id == self.id:
                    return f.center
        elif self.type == "Surface":
            return self._app.modeler.get_object_from_name(self.geometry_assignment).faces[0].center
