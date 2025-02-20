"""
General: coordinate system creation
-----------------------------------
This example shows how you can use PyAEDT to create and modify coordinate systems in the modeler.
"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports

import os

import pyaedt

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

###############################################################################
# Launch AEDT in graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT 2023 R2 in graphical mode.

d = pyaedt.launch_desktop(specified_version="2023.2", non_graphical=non_graphical, new_desktop_session=True)

###############################################################################
# Insert HFSS design
# ~~~~~~~~~~~~~~~~~~
# Insert an HFSS design with the default name.

hfss = pyaedt.Hfss(projectname=pyaedt.generate_unique_project_name(folder_name="CoordSysDemo"))

###############################################################################
# Create coordinate system
# ~~~~~~~~~~~~~~~~~~~~~~~~
# The coordinate system is centered on the global origin and has the axis
# aligned to the global coordinate system. The new coordinate system is
# saved in the object ``cs1``.

cs1 = hfss.modeler.create_coordinate_system()

###############################################################################
# Modify coordinate system
# ~~~~~~~~~~~~~~~~~~~~~~~~
# The ``cs1`` object exposes properties and methods to manipulate the
# coordinate system. The origin can be changed.

cs1["OriginX"] = 10
cs1.props["OriginY"] = 10
cs1.props["OriginZ"] = 10

# Pointing vectors can be changed

ypoint = [0, -1, 0]
cs1.props["YAxisXvec"] = ypoint[0]
cs1.props["YAxisYvec"] = ypoint[1]
cs1.props["YAxisZvec"] = ypoint[2]

###############################################################################
# Rename coordinate system
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Rename the coordinate system.

cs1.rename("newCS")

###############################################################################
# Change coordinate system mode
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Use the ``change_cs_mode`` method to change the mode. Options are ``0``
# for axis/position, ``1`` for Euler angle ZXZ, and ``2`` for Euler angle ZYZ.
# Here ``1`` sets Euler angle ZXZ as the mode.

cs1.change_cs_mode(1)

# In the new mode, these properties can be edited
cs1.props["Phi"] = "10deg"
cs1.props["Theta"] = "22deg"
cs1.props["Psi"] = "30deg"

###############################################################################
# Delete coordinate system
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Delete the coordinate system.

cs1.delete()

###############################################################################
# Create coordinate system by defining axes
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a coordinate system by defining the axes. During creation, you can
# specify all coordinate system properties.

cs2 = hfss.modeler.create_coordinate_system(
    name="CS2", origin=[1, 2, 3.5], mode="axis", x_pointing=[1, 0, 1], y_pointing=[0, -1, 0]
)

###############################################################################
# Create coordinate system by defining Euler angles
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a coordinate system by defining Euler angles.

cs3 = hfss.modeler.create_coordinate_system(name="CS3", origin=[2, 2, 2], mode="zyz", phi=10, theta=20, psi=30)

###############################################################################
# Create coordinate system by defining view
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a coordinate system by defining the view. Options are ``"iso"``,
# ``"XY"``, ``"XZ"``, and ``"XY"``. Here ``"iso"`` is specified.
# The axes are set automatically.

cs4 = hfss.modeler.create_coordinate_system(name="CS4", origin=[1, 0, 0], reference_cs="CS3", mode="view", view="iso")

###############################################################################
# Create coordinate system by defining axis and angle rotation
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a coordinate system by defining the axis and angle rotation. When you
# specify the axis and angle rotation, this data is automatically translated
# to Euler angles.

cs5 = hfss.modeler.create_coordinate_system(name="CS5", mode="axisrotation", u=[1, 0, 0], theta=123)

###############################################################################
# Create face coordinate system
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Face coordinate systems are bound to an object face.
# First create a box and then define the face coordinate system on one of its
# faces. To create the reference face for the face coordinate system, you must 
# specify starting and ending points for the axis.

box = hfss.modeler.create_box([0, 0, 0], [2, 2, 2])
face = box.faces[0]
fcs1 = hfss.modeler.create_face_coordinate_system(
    face=face, origin=face.edges[0], axis_position=face.edges[1], name="FCS1"
)

###############################################################################
# Create face coordinate system centered on face
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a face coordinate system centered on the face with the X axis pointing
# to the edge vertex.

fcs2 = hfss.modeler.create_face_coordinate_system(
    face=face, origin=face, axis_position=face.edges[0].vertices[0], name="FCS2"
)

###############################################################################
# Swap X and Y axes of face coordinate system
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Swap the X axis and Y axis of the face coordinate system. The X axis is the
# pointing ``axis_position`` by default. You can optionally select the Y axis.

fcs3 = hfss.modeler.create_face_coordinate_system(face=face, origin=face, axis_position=face.edges[0], axis="Y")

# Axis can also be changed after coordinate system creation
fcs3.props["WhichAxis"] = "X"

###############################################################################
# Apply a rotation around Z axis
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Apply a rotation around the Z axis. The Z axis of a face coordinate system
# is always orthogonal to the face. A rotation can be applied at definition.
# Rotation is expressed in degrees.

fcs4 = hfss.modeler.create_face_coordinate_system(face=face, origin=face, axis_position=face.edges[1], rotation=10.3)

# Rotation can also be changed after coordinate system creation
fcs4.props["ZRotationAngle"] = "3deg"

###############################################################################
# Apply offset to X and Y axes of face coordinate system
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Apply an offset to the X axis and Y axis of a face coordinate system.
# The offset is in respect to the face coordinate system itself.

fcs5 = hfss.modeler.create_face_coordinate_system(
    face=face, origin=face, axis_position=face.edges[2], offset=[0.5, 0.3]
)

# The offset can also be changed after the coordinate system is created.
fcs5.props["XOffset"] = "0.2mm"
fcs5.props["YOffset"] = "0.1mm"

###############################################################################
# Create coordinate system relative to face coordinate system
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a coordinate system relative to a face coordinate system. Coordinate
# systems and face coordinate systems interact with each other.

face = box.faces[1]
fcs6 = hfss.modeler.create_face_coordinate_system(face=face, origin=face, axis_position=face.edges[0])
cs_fcs = hfss.modeler.create_coordinate_system(
    name="CS_FCS", origin=[0, 0, 0], reference_cs=fcs6.name, mode="view", view="iso"
)

###############################################################################
# Get all coordinate systems
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get all coordinate systems.

css = hfss.modeler.coordinate_systems
names = [i.name for i in css]
print(names)

###############################################################################
# Select coordinate system
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Select an existing coordinate system.

css = hfss.modeler.coordinate_systems
cs_selected = css[0]
cs_selected.delete()

###############################################################################
# Get point coordinate under another coordinate system
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get a point coordinate under another coordinate system. A point coordinate
# can be translated in respect to any coordinate system.

hfss.modeler.create_box([-10, -10, -10], [20, 20, 20], "Box1")
p = hfss.modeler["Box1"].faces[0].vertices[0].position
print("Global: ", p)
p2 = hfss.modeler.global_to_cs(p, "CS5")
print("CS5 :", p2)

###############################################################################
# Close AEDT
# ~~~~~~~~~~
# After the simulaton completes, you can close AEDT or release it using the
# :func:`pyaedt.Desktop.release_desktop` method.
# All methods provide for saving the project before closing.

d.release_desktop()
