import os

from pyaedt import pyaedt_function_handler
from pyaedt.modeler.geometry_operators import GeometryOperators


class Part(object):
    """Manages 3D component placement and definition.

    Parameters
    ----------
    part_folder : str
        Path to the folder with the A3DCOMP files.
    part_dict : dict
        Defines relevant properties of the class with the following keywords:
        * 'comp_name': str, Name of the A3DCOMP file.
        * 'offset': list or str, Offset coordinate system definition relative to the parent.
        * 'rotation_cs': list or str, Rotation coordinate system relative to the parent.
        * 'rotation': str or numeric, Rotation angle.
        * 'compensation_angle': str or numeric, Initial angle.
        * 'rotation_axis': str, Rotation axis (``"X"``, ``"Y"``, or ``"Z"``).
        * 'duplicate_number': str or int, Number of instances for linear duplication.
        * 'duplicate_vector': list, Vector for duplication relative to the parent coordinate system.
    parent :  str
        The default is ``None``.
    name : str, optional
        Name of the A3DCOMP file without the extension. The default is ``None``.
    """

    # List of known keys for a part and default values:
    allowed_keys = {
        "comp_name": None,  # *.a3dcomp file name
        "offset": None,
        "rotation_cs": None,
        "rotation": 0.0,
        "compensation_angle": None,
        "rotation_axis": "Z",
        "tire_radius": None,
        "duplicate_number": None,
        "duplicate_vector": None,
        "antenna_type": None,  # Antenna only
        "ffd_name": None,  # Antenna only
        "mode": None,  # Antenna only
        "aedt_name": None,
        "beamwidth_elevation": None,  # Antenna only
        "beamwidth_azimuth": None,  # Antenna only
        "polarization": None,
    }  # Antenna only

    def __init__(self, part_folder, part_dict, parent=None, name=None):
        # Default values:
        self._compdef = dict()
        self._multiparts = parent

        # Extract the 3D component name and part folder
        # from the file name.
        # Use this as the default value for comp_name.  Ensure that the correct extension is used.
        self._compdef["part_folder"] = part_folder
        for k in Part.allowed_keys:
            if k in part_dict:
                self._compdef[k] = part_dict[k]
            else:
                self._compdef[k] = Part.allowed_keys[k]

        self._motion = False
        if parent:  # Inherit _motion directly from parent.
            self._motion = self._multiparts.motion

        # make sure self._name is unique if it is not passed as an argument.
        if name:
            self._name = name  # Part name should be unique. No checking here.
        elif "name" in part_dict:
            self._name = part_dict["name"]
        else:
            self._name = "radar"  # TODO: Need to fix this!

        # Update self._compdef from the library definition in the *.json file.

        for kw, val in part_dict.items():
            if kw in self._compdef:
                self._compdef[kw] = val
            else:
                raise KeyError("Key " + kw + " not allowed.")

        # Instantiate yaw, pitch and roll.  Might want to change
        # how this is handled. Make "rotation" a list instead of
        # using .yaw, .pitch, .roll properties?
        self.rot_axis = [False, False, False]  # [X, Y, Z] rotation Boolean
        if self._compdef["rotation_axis"]:
            rotations_axis = self._compdef["rotation_axis"].split(",")
            if self._compdef["rotation"]:
                rotations = self._compdef["rotation"].split(",")
            else:
                rotations = []
            r = "0"
            p = "0"
            y = "0"
            for i, a in enumerate(rotations):
                if rotations_axis[i].lower() == "x":  # roll
                    r = a
                    self.rot_axis[2] = True
                elif rotations_axis[i].lower() == "y":  # pitch
                    p = a
                    self.rot_axis[1] = True
                elif rotations_axis[i].lower() == "z":  # yaw
                    y = a
                    self.rot_axis[0] = True

            self._yaw = y
            self._pitch = p
            self._roll = r
        else:
            self._yaw = "0"
            self._pitch = "0"
            self._roll = "0"

    def __setitem__(self, key, value):
        self._compdef[key] = value

    def __getitem__(self, key):
        if key == "rotation_cs":
            cs = self._compdef[key]
            if cs == "Global" or cs is None:
                self._compdef[key] = ["0", "0", "0"]
            else:
                self._compdef[key] = [str(i) if i is not str else i for i in cs]
        return self._compdef[key]

    @pyaedt_function_handler()
    def zero_offset(self, kw):  # Returns True if cs at kw is at [0, 0, 0]
        """Check if the coordinate system defined by kw is [0, 0, 0].

        Parameters
        ----------
        kw : str
             Coordinate system for kw. Options are ``offset`` and ``rotation_cs``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if kw in ["offset", "rotation_cs"]:
            s = []
            if self[kw]:
                s = [GeometryOperators.is_small(c) for c in self[kw]]
            if len(s) > 0:
                return all(s)
            else:
                return True
        return False

    @property
    def file_name(self):
        """Antenna file name.

        Returns
        -------
        str
            Full name of the A3DCOMP file.
        """
        return os.path.join(self._compdef["part_folder"], self["comp_name"])

    # Create a unique coordinate system name for the part.
    @property
    def cs_name(self):
        """Coordinate system name.

        Returns
        -------
        str
            Name of the coordinate system.
        """
        if self._motion or not self.zero_offset("offset") or not self.zero_offset("rotation_cs"):
            return self.name + "_cs"
        else:
            return self._multiparts.cs_name

    # Define the variable names for angles in the app:
    @property
    def yaw_name(self):
        """Yaw variable name. Yaw is the rotation about the object's Z-axis.

        Returns
        -------
        str
            ame of the yaw variable.

        """
        return self.name + "_yaw"

    @property
    def pitch_name(self):
        """Pitch variable name. Pitch is the rotation about the object's Y-axis.

        Returns
        -------
        str
            Name of the pitch variable.
        """
        return self.name + "_pitch"

    @property
    def roll_name(self):
        """Roll variable name. Roll is the rotation about the object's X-axis.

        Returns
        -------
        str
             Name of the roll variable.
        """
        return self.name + "_roll"

    # Always return the local origin as a list:
    @property
    def local_origin(self):
        """Local part offset values.

        Returns
        -------
        list
            List of offset values for the local part.
        """
        if self["offset"]:
            if self.zero_offset("offset") or self["offset"] == "Global":
                return [0, 0, 0]
            else:
                if self._multiparts._local_units:
                    units = self._multiparts._local_units
                else:
                    units = self._multiparts.modeler_units
                offset = [str(i) + units for i in self["offset"]]

                return offset
        else:
            return [0, 0, 0]

    @property
    def rotate_origin(self):
        """Origin rotation list.

        Returns
        -------
        list
            List of offset values for the rotation.
        """
        if self["rotation_cs"]:
            if self.zero_offset("rotation_cs") or self["rotation_cs"] == "Global":
                return self.local_origin
            else:
                return self["rotation_cs"]
        else:
            return [0, 0, 0]

    @property
    def _do_rotate(self):  # True if any rotation angles are non-zero or 'rotation_cs' is defined.
        return any(self.rot_axis)

    @property
    def _do_offset(self):  # True if any rotation angles are non-zero.
        return any(GeometryOperators.numeric_cs(self.local_origin))

    # Allow expressions should be valid angle as either string
    # or numerical value.
    @property
    def yaw(self):
        """Yaw variable value.

        Returns
        -------
        str
            Value for the yaw variable.
        """
        return self._yaw

    @yaw.setter
    def yaw(self, yaw):
        self._yaw = yaw

    @property
    def pitch(self):
        """Pitch variable value.

        Returns
        -------
        str
            Value of the pitch variable.
        """
        return self._pitch

    @pitch.setter
    def pitch(self, pitch):
        self._pitch = pitch

    @property
    def roll(self):
        """Roll variable value.

        Returns
        -------
        str
            Value of the roll variable.
        """
        return self._roll

    @roll.setter
    def roll(self, roll):
        self._roll = roll

    @property
    def name(self):
        """Part name.

        Returns
        -------
        str
            Name of the part.
        """
        return self._multiparts.name + "_" + self._name

    @pyaedt_function_handler()
    def set_relative_cs(self, app):
        """Create a parametric coordinate system.

        Parameters
        ----------
        app : pyaedt.Hfss

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        # Set x, y, z offset variables in app. But check first to see if the CS
        # has already been defined.
        if self.cs_name not in app.modeler.oeditor.GetCoordinateSystems() and self.cs_name != "Global":
            x_pointing = [1, 0, 0]
            y_pointing = [0, 1, 0]
            app.modeler.create_coordinate_system(
                origin=self.local_origin,
                x_pointing=x_pointing,
                y_pointing=y_pointing,
                reference_cs=self._multiparts.cs_name,
                mode="axis",
                name=self.cs_name,
            )
        return True

    @property
    def rot_cs_name(self):
        """Rotation coordinate system name.

        Returns
        -------
        str
            Name of the rotation coordinate system.
        """
        return self.name + "_rot_cs"

    @pyaedt_function_handler()
    def do_rotate(self, app, aedt_object):
        """Set the rotation coordinate system relative to the parent coordinate system.

        This method should only be called if there is rotation in the component.
        The rotation coordinate system is offset from the parent coordinate system.

        Parameters
        ----------
        app : pyaedt.Hfss
            HFSS application instance.
        aedt_object : str
            Name of the HFSS design.
        """
        x_pointing = [1, 0, 0]
        y_pointing = [0, 1, 0]
        app.modeler.create_coordinate_system(
            origin=self.rotate_origin,
            x_pointing=x_pointing,
            y_pointing=y_pointing,
            reference_cs=self._multiparts.cs_name,
            mode="axis",
            name=self.rot_cs_name,
        )
        if self.rot_axis[0]:
            app[self.yaw_name] = self.yaw
            app.modeler.rotate(aedt_object, "Z", angle=self.yaw_name)
        if self.rot_axis[1]:
            app[self.pitch_name] = self.pitch
            app.modeler.rotate(aedt_object, "Y", angle=self.pitch_name)
        if self.rot_axis[2]:
            app[self.roll_name] = self.roll
            app.modeler.rotate(aedt_object, "X", angle=self.roll_name)

        return True

    @pyaedt_function_handler()
    def insert(self, app):
        """Insert 3D component in AEDT.

        Parameters
        ----------
        app : pyaedt.Hfss

        Returns
        -------
        str
            Name of inserted object.
        """
        aedt_objects = []
        # TODO: Why the inconsistent syntax for cs commands?
        if self._do_offset:
            self.set_relative_cs(app)  # Create coordinate system, if needed.
            comp_obj = app.modeler.insert_3d_component(self.file_name, targetCS=self.cs_name)
            aedt_objects.append(comp_obj.name)
        else:
            comp_obj = app.modeler.insert_3d_component(self.file_name, targetCS=self._multiparts.cs_name)
            aedt_objects.append(comp_obj.name)
        if self._do_rotate:
            self.do_rotate(app, aedt_objects[0])

        # Duplication occurs in parent coordinate system.
        app.modeler.set_working_coordinate_system(self._multiparts.cs_name)
        if self["duplicate_vector"]:
            d_vect = [float(i) for i in self["duplicate_vector"]]
            duplicate_result = app.modeler.duplicate_along_line(
                aedt_objects[0], d_vect, nclones=int(self["duplicate_number"]), is_3d_comp=True
            )
            if duplicate_result[0]:
                for d in duplicate_result[1]:
                    aedt_objects.append(d)
        return aedt_objects


class Antenna(Part, object):
    """Manages antennas.

    This class is derived from :class:`Part`.

    Parameters
    ----------
    root_folder : str
        Root directory
    ant_dict : dict
        Antenna dictionary
    parent : str, optional
        The default is ``None``.
    name : str, optional
        The default is ``None``.

    """

    def __init__(self, root_folder, ant_dict, parent=None, name=None):
        super(Antenna, self).__init__(root_folder, ant_dict, parent=parent, name=name)

    def _antenna_type(self, app):
        if self._compdef["antenna_type"] == "parametric":
            return app.SbrAntennas.ParametricBeam
        if self._compdef["antenna_type"] == "ffd":
            return "file"

    @property
    def params(self):
        """Multi-part component parameters.

        Returns
        -------
        dict
            Dictionary of parameters for a multi-part component.
        """
        p = {}
        if self._compdef["antenna_type"] == "parametric":
            p["Vertical BeamWidth"] = self._compdef["beamwidth_elevation"]
            p["Horizontal BeamWidth"] = self._compdef["beamwidth_azimuth"]
            p["Polarization"] = self._compdef["polarization"]
        return p

    @pyaedt_function_handler()
    def _insert(self, app, target_cs=None, units=None):
        if not target_cs:
            target_cs = self._multiparts.cs_name
        if not units:
            if self._multiparts._local_units:
                units = self._multiparts._local_units
            else:
                units = self._multiparts.units
        if self._compdef["ffd_name"]:
            ffd = os.path.join(self._compdef["part_folder"], self._compdef["ffd_name"] + ".ffd")
            a = app.create_sbr_file_based_antenna(
                ffd_full_path=ffd, model_units=units, target_cs=target_cs, antenna_name=self.name
            )
        else:
            a = app.create_sbr_antenna(
                self._antenna_type(app),
                model_units=units,
                parameters_dict=self.params,
                target_cs=target_cs,
                antenna_name=self.name,
            )
        return a

    @pyaedt_function_handler()
    def insert(self, app, units=None):
        """Insert antenna in HFSS SBR+.

        Parameters
        ----------
        app : pyaedt.Hfss
        units :
            The default is ``None``.

        Returns
        -------
        str
            Name of the inserted object.
        """
        if self._do_offset:
            self.set_relative_cs(app)
            antenna_object = self._insert(app, target_cs=self.cs_name, units=units)
        else:
            antenna_object = self._insert(app, target_cs=self._multiparts.cs_name, units=units)
        if self._do_rotate and antenna_object:
            self.do_rotate(app, antenna_object.name)

        return antenna_object
