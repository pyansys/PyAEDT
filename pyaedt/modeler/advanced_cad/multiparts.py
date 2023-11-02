# -*- coding: utf-8 -*-
import os

from pyaedt.generic.DataHandlers import json_to_dict
from pyaedt.generic.filesystem import get_json_files
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.advanced_cad.parts import Antenna, Part
from pyaedt.modeler.geometry_operators import GeometryOperators


class MultiPartComponent(object):
    """Supports multi-part 3D components for HFSS SBR+.

    .. note::
           Forward motion is in the X-axis direction if motion is set.

    Parameters
    ----------
    comp_folder : str
        Full path to the folder with the JSON file containing the component definition.
        This JSON file must have the same name as the folder.
    name : str, optional
        Name of the multipart component. If this value is set, the
        component is selected from the corresponding JSON file in
        ``comp_folder``. The default is ``None``, in which case the
        name of the first JSON file in the folder is used.
    use_relative_cs : bool, optional
        Whether to use the relative coordinate system. The default is ``False``.
        Set to ``False`` if the multi-part component doesn't move. Set to ``True``
        if the multi-part component moves relative to the global coordinate system.
    relative_cs_name : str, optional
        Name of the coordinate system to connect the multipart relative system to
        when ``use_relative_cs=True``.
    motion : bool, optional
        Whether expressions should be used to define the position and orientation of
        the multi-part component. The default is ``False``.
    offset : list, optional
        List of ``[x, y, z]`` coordinate values defining the component offset.
        The default is ``["0", "0", "0"]``.
    yaw : str or float, optional
        Yaw angle, indicating the rotation about the component's Z-axis. The default
        is ``"0deg"``.
    pitch : str or float, optional
        Pitch angle, indicating the rotation about the component Y-axis The default
        is ``"0deg"``.
    roll : str or float, optional
        Roll angle, indicating the rotation about the component X-axis. The default
        is ``"0deg"``.
    roll : str or float, optional
        Roll angle, indicating the rotation about the component's X-axis. The default

    """

    _component_classes = ["environment", "rcs_standard", "vehicle", "person", "bike", "bird", "radar"]

    # Keep track of all assigned names to the class. Use the
    # properties '.name' and '.index' to ensure unique instance names.
    _names = []
    # for c in _component_classes:
    #     _count[c] = 0

    # Initialize variables and values for the app using
    # the MultiPartComponent
    _t = "time_var"
    _t_value = "0s"
    modeler_units = "meter"

    @staticmethod
    def start(app):
        """Initialize app for SBR+ simulation.

        Parameters
        ----------
        app : class:`pyaedt.Hfss`
            HFSS application instance.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        app[MultiPartComponent._t] = MultiPartComponent._t_value
        app.modeler.model_units = "meter"  # Set units.

        return True

    def __init__(
        self,
        comp_folder,
        name=None,
        use_relative_cs=False,
        relative_cs_name=None,
        motion=False,
        offset=("0", "0", "0"),
        yaw="0deg",
        pitch="0deg",
        roll="0deg",
    ):
        self.comp_folder = comp_folder  # Folder where the component is defined.
        # self._name = os.path.split(comp_folder)[-1]  # Base name of multipart component.
        self._index = None  # Counter used to assign unique name.
        self._yaw = yaw  # Yaw is the rotation about the z-axis
        self._pitch = pitch  # Pitch is tilt toward the sky (i.e. rotation about y)
        self._roll = roll  # Roll is rotation about the x-axis (x is the direction of movement)
        self._relative_cs_name = relative_cs_name
        if relative_cs_name:
            self._reference_cs_name = relative_cs_name
        else:
            self._reference_cs_name = "Global"

        # If the component moves, then expressions must be used for position and orientation
        self.motion = motion

        self.aedt_components = []  # List of components

        # Find the json file that defines this part.
        json_files = get_json_files(self.comp_folder)
        if name:
            self._name = name  # Define name from the passed parameter.
            f = None
            for fn in json_files:
                if os.path.split(fn)[1].split(".")[0] == name:
                    f = fn
        else:
            f = json_files[0]
            self._name = os.path.split(f)[1].split(".")[0]  # Define name from the json file name.

        compdef = json_to_dict(f)  # dict defining the 3d component

        if "class" in compdef.keys():
            self._component_class = compdef["class"]
        elif self._component_class:  # already defined by subclass. Do nothing.
            pass
        else:
            self._component_class = None

        #  Allow for different units in the multipart component. For example with radar.
        if "units" in compdef.keys():
            self._local_units = compdef["units"]
        else:
            self._local_units = None  # Default to global units.

        # Used to offset the multipart component.
        # These are the variable names in HFSS.
        # self.name is a unique name (see the @property definition for name)
        xyz = ["x", "y", "z"]
        self._offset_var_names = [self.name + "_" + s for s in xyz]

        # Instantiate parts with the Part class.
        self.parts = {}
        if "parts" in compdef.keys():
            for pn, part_def in compdef["parts"].items():
                self.parts[pn] = Part(self.comp_folder, part_def, parent=self, name=pn)
        if "antennas" in compdef.keys():
            for a, a_def in compdef["antennas"].items():
                self.parts[a] = Antenna(self.comp_folder, a_def, parent=self, name=a)

        self.use_relative_cs = use_relative_cs
        if use_relative_cs:
            self._use_global_cs = False
            self._offset_values = list(offset)

        else:
            self._use_global_cs = True
            self._offset_values = list(offset)

    @property
    def cs_name(self):
        """Coordinate system name.

        Returns
        -------
        str
            Name of the coordinate system.
        """
        if self.use_global_cs:
            self._relative_cs_name = "Global"
        elif not self._relative_cs_name:
            self._relative_cs_name = self.name + "_cs"
        return self._relative_cs_name

    @property
    def index(self):
        """Number of multi-part components.

        Returns
        -------
        int
           Number of multi-part components.
        """
        if self._index is None:  # Only increment one time.
            self._index = MultiPartComponent._names.count(self._name)
            MultiPartComponent._names.append(self._name)
        return self._index

    # The following read-only properties are used to
    # set the x,y,z offset variable name for this
    # multi-part 3d component instance in the app.
    @property
    def offset_x_name(self):
        """X-axis offset name.

        Returns
        -------
        str
            Name of the X-axis offset.
        """
        return self._offset_var_names[0]

    @property
    def offset_y_name(self):
        """Y-axis offset name.

        Returns
        -------
        str
            Name of the Y-axis offset.
        """
        return self._offset_var_names[1]

    @property
    def offset_z_name(self):
        """Z-axis offset name.

        Returns
        -------
        str
            Name of the Z-axis offset.
        """
        return self._offset_var_names[2]

    @property
    def offset_names(self):
        """X-, Y-, and Z-axis offset names.

        Returns
        -------
        list
            List of the offset names for the X-, Y-, and Z-axes.
        """
        return [self.offset_x_name, self.offset_y_name, self.offset_z_name]

    @property
    def yaw_name(self):
        """Yaw variable name. Yaw is the rotation about the object's Z-axis.

        Returns
        -------
        str
            Name of the yaw variable.
        """
        return self.name + "_yaw"

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
    def yaw(self, yaw_str):
        # TODO: Need variable checking for yaw angle.
        # yaw is the rotation about the object z-axis.
        self._use_global_cs = False
        self._yaw = yaw_str

    @property
    # This is the name of the variable for pitch in the app.
    def pitch_name(self):
        """Pitch variable name. Pitch is the rotation about the object's Y-axis.

        Returns
        -------
        str
            Name of the pitch variable.
        """
        return self.name + "_pitch"

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
    def pitch(self, pitch_str):
        # TODO: Need variable checking for pitch angle.
        # pitch is the rotation about the object y-axis.
        self._use_global_cs = False
        self._pitch = pitch_str

    @property
    # This is the name of the variable for roll in the app.
    def roll_name(self):
        """Roll variable name. Roll is the rotation about the object's X-axis.

        Returns
        -------
        str
            Name of the roll variable.
        """
        return self.name + "_roll"

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
    def roll(self, roll_str):
        # TODO: Need variable checking for pitch angle.
        # roll is the rotation about the object x-axis.
        self._use_global_cs = False
        self._roll = roll_str

    @property
    def _cs_pointing(self):
        if self.motion:  # Pass expressions to the app variable.
            yaw_str = self.yaw_name
            pitch_str = self.pitch_name
            roll_str = self.roll_name
        else:  # Pass values to the app variable.
            yaw_str = self.yaw
            pitch_str = self.pitch
            roll_str = self.roll

        return GeometryOperators.cs_xy_pointing_expression(yaw_str, pitch_str, roll_str)

    @property
    def name(self):
        """Unique instance name.

        Returns
        -------
        str
           Name of the unique instance.
        """
        suffix = "_" + str(self.index)
        return self._name + suffix  # unique instance name

    @property
    def use_global_cs(self):
        """Global coordinate system.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        return self._use_global_cs

    @property
    def offset(self):
        """Offset values for the multi-part component.

        Returns
        -------
        list
            List of offset values.
        """
        return self._offset_values

    @offset.setter
    def offset(self, o):
        # TODO: Add check for validity
        self._use_global_cs = False
        self._offset_values = o  # Expect tuple or list of strings

    @pyaedt_function_handler()
    def position_in_app(self, app):
        """Set up design variables and values to enable motion for the multi-part 3D component.

        Parameters
        ----------
        app : pyaedt.Hfss
            HFSS application instance.

        Returns
        -------
        :class:`pyaedt.modeler.Modeler.CoordinateSystem`
        """
        if self.motion:
            xyz = ["x", "y", "z"]
            for m in range(3):
                # app[self.offset_names[m]] = self.offset[m]
                app.variable_manager.set_variable(
                    variable_name=self.offset_names[m],
                    expression=self.offset[m],
                    description=self.name + " " + xyz[m] + "-position",
                )
            app.variable_manager.set_variable(
                variable_name=self.yaw_name, expression=self.yaw, description=self.name + " yaw"
            )

            app.variable_manager.set_variable(
                variable_name=self.pitch_name, expression=self.pitch, description=self.name + " pitch"
            )

            app.variable_manager.set_variable(
                variable_name=self.roll_name, expression=self.roll, description=self.name + " roll"
            )

            cs_origin = self.offset_names
        else:
            cs_origin = self.offset
        if self.use_relative_cs:
            return app.modeler.create_coordinate_system(
                origin=cs_origin,
                reference_cs=self._reference_cs_name,
                x_pointing=self._cs_pointing[0],
                y_pointing=self._cs_pointing[1],
                mode="axis",
                name=self.cs_name,
            )

    @pyaedt_function_handler()
    def _insert(self, app, motion=False):
        """Insert the multi-part 3D component.

        Parameters
        ----------
        app : :class:`pyaedt.hfss.Hfss`
            HFSS application where multi-part component is to be inserted.
        motion : bool, optional
            Whether variables (yaw, pitch, and roll) should be created in the app to set position.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.motion = True if motion else self.motion

        if self.use_global_cs or self.cs_name in app.modeler.oeditor.GetCoordinateSystems():
            app.modeler.set_working_coordinate_system(self.cs_name)
            if self.use_relative_cs:
                self._relative_cs_name = self.name + "_cs"
        self.position_in_app(app)

        for p in self.parts:
            inserted = self.parts[p].insert(app)  # index ensures unique CS names.
            if len(inserted) > 0:
                for i in inserted:
                    self.aedt_components.append(i)
        app.modeler.create_group(components=self.aedt_components, group_name=self.name)
        return True

    @pyaedt_function_handler()
    def insert(self, app, motion=False):
        """Insert the object in HFSS SBR+.

        Returns
        -------
        bool
        """
        return self._insert(app, motion=motion)


class Environment(MultiPartComponent, object):
    """Supports multi-part 3D components without motion for HFSS SBR+.

    This class is derived from :class:`MultiPartComponent`. Its
    call signature is identical to the parent class except
    ``motion`` is always set to ``False``.

    Parameters
    ----------
    env_folder : str
        Full path to the folder with the JSON file containing the component definition.
    relative_cs_name : str, optional
        Name of the coordinate system to connect the component's relative system to
        when ``use_relative_cs=True``. The default is ``None``, in which case the
        global coordinate system is used.
    """

    def __init__(self, env_folder, relative_cs_name=None):
        super(Environment, self).__init__(env_folder, motion=False)

    @property
    def cs_name(self):
        """Coordinate system name.

        Returns
        -------
        str
            Name of the coordinate system.
        """
        return "Global"

    @property
    def yaw(self):
        """Yaw variable value. Yaw is the rotation about the object's Z-axis.

        Returns
        -------
        str
            Value for the yaw variable.
        """
        return self._yaw

    @yaw.setter
    def yaw(self, yaw_str):
        self._yaw = yaw_str

    @property
    def pitch(self):
        """Pitch variable value. Pitch is the rotation about the object's Y-axis.

        Returns
        -------
        str
            Value for the pitch variable.
        """
        return self._pitch

    @pitch.setter
    def pitch(self, pitch_str):
        self._pitch = pitch_str

    @property
    def roll(self):
        """Roll variable value. Roll is the rotation about the object's X-axis.

        Returns
        -------
        str
            Value for the roll variable.
        """
        return self._roll

    @roll.setter
    def roll(self, roll_str):
        self._roll = roll_str

    @property
    def offset(self):
        """Offset for the multi-part component.

        Returns
        -------
        list
        """
        return self._offset_values

    @offset.setter
    def offset(self, o):
        if isinstance(o, list) or isinstance(o, tuple) and len(o) == 3:
            self._offset_values = o


class Actor(MultiPartComponent, object):
    """Provides an instance of an actor.

    This class is derived from :class:`MultiPartComponent`.

    .. note::  Motion is always forward in the X-axis direction.

    Parameters
    ----------
    actor_folder : str
        Full path to the folder containing the definition of the person.
        This can be changed later in the :class:`Person` class definition.
    speed : float or str
        Speed of the person in the X-direction. The default is ``0```.
    relative_cs_name : str
        Name of the relative coordinate system of the actor. The default is ``None``,
        in which case the global coordinate system is used.
    """

    def __init__(self, actor_folder, speed="0", relative_cs_name=None):
        super(Actor, self).__init__(actor_folder, use_relative_cs=True, motion=True, relative_cs_name=relative_cs_name)

        self._speed_expression = str(speed) + "m_per_sec"  # TODO: Need error checking here.

    @property
    def speed_name(self):
        """Speed variable name.

        Returns
        -------
        str
            Name of the speed variable.
        """
        return self.name + "_speed"

    @property
    def speed_expression(self):
        """Speed variable expression.

        Returns
        -------
        str
            Expression for the speed variable.
        """
        return self._speed_expression

    @speed_expression.setter
    def speed_expression(self, s):  # TODO: Add validation of the expression.
        self._speed_expression = s

    @pyaedt_function_handler()
    def _add_speed(self, app):
        app.variable_manager.set_variable(
            variable_name=self.speed_name, expression=self.speed_expression, description="object speed"
        )
        # Update expressions for x and y position in app:
        app[self.offset_names[0]] = (
            str(self.offset[0]) + "+" + self.speed_name + " * " + MultiPartComponent._t + "* cos(" + self.yaw_name + ")"
        )

        app[self.offset_names[1]] = (
            str(self.offset[1]) + "+" + self.speed_name + " * " + MultiPartComponent._t + "* sin(" + self.yaw_name + ")"
        )
