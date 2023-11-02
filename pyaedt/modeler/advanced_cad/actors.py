from pyaedt import pyaedt_function_handler
from pyaedt.generic.DataHandlers import json_to_dict
from pyaedt.modeler.advanced_cad.multiparts import Actor, MultiPartComponent


def read_actors(fn, actor_lib):
    """Read and map actors in a JSON file to a list of actor objects.

    Parameters
    ----------
    fn : str
        Name of the JSON file describing the actors.
    actor_lib : str
        Full path to the library containing the actor definitions.

    Returns
    -------
    list
        List of actor objects.
    """
    a = {}
    actor_dict = json_to_dict(fn)
    for name in actor_dict:
        a[name] = Actor(actor_dict[name], actor_lib, name)
    return a


class Generic(Actor, object):
    """Provides an instance of an actor.

    This class is derived from :class:`pyaedt.modeler.multiparts.MultiPartComponent`.

    .. note::
       Motion is always forward in the X-axis direction of the person
       coordinate system.

    Parameters
    ----------
    actor_folder : str
        Full path to the directory containing the definition of the person.
        This can be changed later in the :class:`Person` class definition.
    speed : float or str
        Speed of the person in the X-axis direction.
    relative_cs_name : str
        Name of the relative coordinate system of the actor. The default is ``None``,
        in which case the global coordinate system is used.

    """

    def __init__(self, actor_folder, speed="0", relative_cs_name=None):
        """Generic class."""
        super(Generic, self).__init__(actor_folder, speed=speed, relative_cs_name=relative_cs_name)


class Person(Actor, object):
    """Provides an instance of a person.

    This class is derived from :class:`pyaedt.modeler.multiparts.MultiPartComponent`.

    .. note::
       Motion is always forward in the X-axis direction of the person coordinate system.

    Parameters
    ----------
    actor_folder : str
        Full path to the folder containing the definition of the
        person. This can be changed later in the :class:`Person`
        class definition.
    speed : float or str, optional
        Speed of the person in the X-axis direction. The default is ``"0"``.
    stride : float or str, optional
        Stride length of the person. The default is "0.8meters".
    relative_cs_name : str, optional
        Name of the relative coordinate system of the actor. The
        default is ``None``, in which case the global coordinate
        system is used.

    """

    def __init__(self, actor_folder, speed="0", stride="0.8meters", relative_cs_name=None):
        """Initialize person actor."""
        super(Person, self).__init__(actor_folder, speed=speed, relative_cs_name=relative_cs_name)

        self._stride = stride

    @property
    def stride(self):
        """Stride in meters.

        Returns
        -------
        str
        """
        return self._stride

    @stride.setter
    def stride(self, s):
        self._stride = s  # TODO: Add validation to allow expressions.

    @pyaedt_function_handler()
    def _add_walking(self, app):
        # Update expressions for oscillation of limbs. At this point
        # we could parse p.name to handle motion (arm, leg, ...).
        for k, p in self.parts.items():
            if any(p.rot_axis):  # use this key to determine if there is motion of the part.
                if p.rot_axis[1]:  # Make sure pitch rotation is True
                    app[p.pitch_name] = (
                        p.pitch
                        + "*sin(2*pi*("
                        + self.speed_name
                        + "/"
                        + self.stride
                        + ") "
                        + "*"
                        + MultiPartComponent._t
                        + ") + "
                        + "("
                        + p["compensation_angle"]
                        + ")rad"
                    )

    @pyaedt_function_handler()
    def insert(self, app, motion=True):
        """Insert the person in HFSS SBR+.

        Parameters
        ----------
        app : pyaedt.Hfss
            HFSS application instance.
        motion : bool, optional
            Whether the person is in motion. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        app.logger.info("Adding person: " + self.name)

        # Insert the component first, then set variables.
        self._insert(app)  # Place the person in the app.
        if motion:
            self._add_speed(app)
            self._add_walking(app)


class Bird(Actor, object):
    """Provides an instance of a bird.

    This class is derived from :class:`pyaedt.modeler.multiparts.MultiPartComponent`.

    .. note::
       Motion is always forward in the X-axis direction.

    Parameters
    ----------
    bird_folder : str
        Full path to the directory containing the definition of the
        bird. This can be changed later.
    speed : float or str, optional
        Speed of the bird. The default is ``"2.0"``.
    flapping_rate : float or str, optional
        Flapping rate. The default is ``"50Hz"``.
    relative_cs_name : str, optional
        Name of the relative coordinate system of the actor. The
        default is``None``, in which case the global coordinate system
        is used.

    """

    def __init__(self, bird_folder, speed="2.0", flapping_rate="50Hz", relative_cs_name=None):
        """Bike class."""
        super(Bird, self).__init__(bird_folder, speed=speed, relative_cs_name=relative_cs_name)
        self._flapping_rate = flapping_rate

    def _add_flying(self, app):
        # Update expressions for wheel motion:

        for k, p in self.parts.items():
            if any(p.rot_axis):  # use this key to verify that there is local motion.
                if p.rot_axis[2]:  # Flapping is roll
                    app[p.roll_name] = (
                        p["rotation"] + "* sin(2*pi*" + str(self._flapping_rate) + "*" + MultiPartComponent._t + ")"
                    )

    @pyaedt_function_handler()
    def insert(self, app, motion=True):
        """Insert the bird in HFSS SBR+.

        Parameters
        ----------
        app : pyaedt.Hfss
        motion : bool
            Whether the bird is in motion. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        app.logger.info("Adding Vehicle: " + self.name)

        self._insert(app)  # Place the multipart component in the app.
        if motion:
            self._add_speed(app)
            self._add_flying(app)


class Vehicle(Actor, object):
    """Provides an instance of a vehicle.

    This class is derived from :class:`pyaedt.modeler.multiparts.MultiPartComponent`.

    .. note::
        Motion is always forward in the X-axis direction.

    Parameters
    ----------
    car_folder : str, required
        Full path to the folder containing the definition of the
        vehicle.  This can be changed later.
    speed : float or str, optional
        Speed of the vehicle. The default is ``10.0``.
    relative_cs_name : str, optional
        Name of the relative coordinate system of the actor. The
        default is ``None``, in which case the global coordinate
        system is used.

    """

    def __init__(self, car_folder, speed=10.0, relative_cs_name=None):
        """Vehicle class."""
        super(Vehicle, self).__init__(car_folder, speed=speed, relative_cs_name=relative_cs_name)

    @pyaedt_function_handler()
    def _add_driving(self, app):
        # Update expressions for wheel motion:
        for k, p in self.parts.items():
            if any(p.rot_axis):  # use this key to determine if there is motion of the wheel.
                if p.rot_axis[1]:  # Make sure pitch rotation is True
                    app[p.pitch_name] = (
                        "("
                        + MultiPartComponent._t
                        + "*"
                        + self.speed_name
                        + "/"
                        + p["tire_radius"]
                        + "meter)*(180/pi)*1deg"
                    )

    @pyaedt_function_handler()
    def insert(self, app, motion=True):
        """Insert the vehicle in HFSS SBR+.

        Parameters
        ----------
        app : pyaedt.Hfss
        motion : bool, optional
            Whether the vehicle is in motion. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        app.logger.info("Adding vehicle: " + self.name)

        self._insert(app)  # Place the multipart component in the app.
        if motion:
            self._add_speed(app)
            self._add_driving(app)
        return True


class Radar(MultiPartComponent, object):
    """Manages the radar definition and placement in the HFSS design.

    Parameters
    ----------
    radar_folder : str
        Full path to the folder containing the radar file.
    name : str, optional
        Name of the radar file. The default is ``None``.
    motion : bool, optional
        Whether the actor is in motion. The default is ``False``.
    use_relative_cs : bool, optional
        Whether to use the relative coordinate system. The default is ``False``.
    offset : list, optional
        List of offset values. The default is ``("0", "0", "0")``.
    speed : float or str, optional
        Speed of the vehicle. The default is ``0``.
    relative_cs_name : str, optional
        Name of the relative coordinate system of the actor. The
        default is ``None``, in which case the global coordinate
        system is used.

    """

    def __init__(
        self,
        radar_folder,
        name=None,
        motion=False,
        use_relative_cs=False,
        offset=("0", "0", "0"),
        speed=0,
        relative_cs_name=None,
    ):
        self.aedt_antenna_names = []  # List of Antenna Names
        name = name.split(".")[0] if name else name  # remove suffix if any
        self._component_class = "radar"
        super(Radar, self).__init__(
            radar_folder,
            name=name,
            use_relative_cs=use_relative_cs,
            motion=motion,
            offset=offset,
            relative_cs_name=relative_cs_name,
        )
        self._speed_expression = str(speed) + "m_per_sec"
        self.pair = []

    @property
    def units(self):
        """Multi-part units.

        Returns
        -------
        str
            Multipart units.
        """
        return self._local_units

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
    def speed_expression(self, s):
        self._speed_expression = s

    @pyaedt_function_handler()
    def _add_speed(self, app):
        app.variable_manager.set_variable(
            variable_name=self.speed_name, expression=self.speed_expression, description="radar speed"
        )
        # Update expressions for x and y position in app:
        app[self.offset_names[0]] = (
            str(self.offset[0]) + "+" + self.speed_name + " * " + MultiPartComponent._t + "* cos(" + self.yaw_name + ")"
        )

        app[self.offset_names[1]] = (
            str(self.offset[1]) + "+" + self.speed_name + " * " + MultiPartComponent._t + "* sin(" + self.yaw_name + ")"
        )

    @pyaedt_function_handler()
    def insert(self, app, motion=False):
        """Insert radar in the HFSS application instance.

        Parameters
        ----------
        app : pyaedt.Hfss
        motion : bool, optional
            Whether the actor is in motion. The default is ``False``.

        Returns
        -------
        list
            List of antennae that have been placed.
        """
        app.logger.info("Adding radar module:  " + self.name)
        if self.use_global_cs or self.cs_name in app.modeler.oeditor.GetCoordinateSystems():
            app.modeler.set_working_coordinate_system(self.cs_name)
            if self.use_relative_cs:
                self._relative_cs_name = self.name + "_cs"
        self.position_in_app(app)
        tx_names = []
        rx_names = []
        for p in self.parts:
            antenna_object = self.parts[p].insert(app, units=self._local_units)
            self.aedt_components.append(antenna_object.name)
            self.aedt_antenna_names.append(antenna_object.excitation_name)
            if p.startswith("tx"):
                tx_names.append(antenna_object.excitation_name)
            elif p.startswith("rx"):
                rx_names.append(antenna_object.excitation_name)

        # Define tx/rx pairs:
        self.pair = {}
        for tx in tx_names:
            rx_string = ""
            for rx in rx_names:
                rx_string += rx + ","
            self.pair[tx] = rx_string.strip(",")

        app.set_sbr_txrx_settings(self.pair)

        app.modeler.create_group(components=self.aedt_components, group_name=self.name)
        app.logger.info("Group Created:  " + self.name)
        if motion:
            self._add_speed(app)
        return self.aedt_antenna_names
