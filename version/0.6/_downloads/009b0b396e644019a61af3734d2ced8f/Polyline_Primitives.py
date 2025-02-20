"""
General: polyline creation
--------------------------
This example shows how you can use PyAEDT to create and manipulate polylines.
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import pyaedt

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False
###############################################################################
# Create Maxwell 3D object
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Create a :class:`pyaedt.maxwell.Maxwell3d` object and set the unit type to ``"mm"``.

M3D = pyaedt.Maxwell3d(solution_type="Transient", designname="test_polyline_3D", specified_version="2023.2",
                       new_desktop_session=True, non_graphical=non_graphical, )
M3D.modeler.model_units = "mm"
prim3D = M3D.modeler

###############################################################################
# Define variables
# ~~~~~~~~~~~~~~~~
# Define two design variables as parameters for the polyline objects.

M3D["p1"] = "100mm"
M3D["p2"] = "71mm"

###############################################################################
# Input data
# ~~~~~~~~~~
# Input data. All data for the polyline functions can be entered as either floating point
# values or strings. Floating point values are assumed to be in model units
# (``M3D.modeler.model_units``).

test_points = [["0mm", "p1", "0mm"], ["-p1", "0mm", "0mm"], ["-p1/2", "-p1/2", "0mm"], ["0mm", "0mm", "0mm"]]

###############################################################################
# Polyline primitives
# -------------------
# The following examples are for creating polyline primitives.

# Create line primitive
# ~~~~~~~~~~~~~~~~~~~~~
# Create a line primitive. The basic polyline command takes a list of positions
# (``[X, Y, Z]`` coordinates) and creates a polyline object with one or more
# segments. The supported segment types are ``Line``, ``Arc`` (3 points),
# ``AngularArc`` (center-point + angle), and ``Spline``.

P = prim3D.create_polyline(position_list=test_points[0:2], name="PL01_line")

print("Created Polyline with name: {}".format(prim3D.objects[P.id].name))
print("Segment types : {}".format([s.type for s in P.segment_types]))
print("primitive id = {}".format(P.id))

###############################################################################
# Create arc primitive
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create an arc primitive. The parameter ``position_list`` must contain at
# least three position values. The first three position values are used.

P = prim3D.create_polyline(position_list=test_points[0:3], segment_type="Arc", name="PL02_arc")

print("Created object with id {} and name {}.".format(P.id, prim3D.objects[P.id].name))

###############################################################################
# Create spline primitive
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a spline primitive. Defining the segment using a ``PolylineSegment``
# object allows you to provide additional input parameters for the spine, such
# as the number of points (in this case 4). The parameter ``position_list``
# must contain at least four position values.

P = prim3D.create_polyline(
    position_list=test_points, segment_type=prim3D.polyline_segment("Spline", num_points=4), name="PL03_spline_4pt"
)

###############################################################################
# Create center-point arc primitive
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a center-point arc primitive. A center-point arc segment is defined
# by a starting point, a center point, and an angle of rotation around the
# center point. The rotation occurs in a plane parallel to the XY, YZ, or ZX
# plane of the active coordinate system. The starting point and the center point
# must therefore have one coordinate value (X, Y, or Z) with the same value.
# 
# Here ``start-point`` and ``center-point`` have a common Z coordinate, ``"0mm"``.
# The curve is therefore rotated in the XY plane with Z = ``"0mm"``.

start_point = [100, 100, 0]
center_point = [0, 0, 0]
P = prim3D.create_polyline(
    position_list=[start_point],
    segment_type=prim3D.polyline_segment("AngularArc", arc_center=center_point, arc_angle="30deg"),
    name="PL04_center_point_arc",
)

###############################################################################
# Here ``start_point`` and ``center_point`` have the same values for the Y and
# Z coordinates, so the plane or rotation could be either XY or ZX.
# For these special cases when the rotation plane is ambiguous, you can specify
# the plane explicitly.

start_point = [100, 0, 0]
center_point = [0, 0, 0]
P = prim3D.create_polyline(
    position_list=[start_point],
    segment_type=prim3D.polyline_segment("AngularArc", arc_center=center_point, arc_angle="30deg", arc_plane="XY"),
    name="PL04_center_point_arc_rot_XY",
)
P = prim3D.create_polyline(
    position_list=[start_point],
    segment_type=prim3D.polyline_segment("AngularArc", arc_center=center_point, arc_angle="30deg", arc_plane="ZX"),
    name="PL04_center_point_arc_rot_ZX",
)

###############################################################################
# Compound polylines
# ------------------ 
# You can use a list of points in a single command to create a multi-segment
# polyline.
#
# By default, if no specification of the type of segments is given, all points
# are connected by line segments.

P = prim3D.create_polyline(position_list=test_points, name="PL06_segmented_compound_line")

###############################################################################
# You can specify the segment type with the parameter ``segment_type``.
# In this case, you must specify that the four input points in ``position_list``
# are to be connected as a line segment followed by a 3-point arc segment.

P = prim3D.create_polyline(position_list=test_points, segment_type=["Line", "Arc"], name="PL05_compound_line_arc")

###############################################################################
# The parameter ``close_surface`` ensures that the polyline starting point and
# ending point are the same. If necessary, you can add an additional line
# segment to achieve this.

P = prim3D.create_polyline(position_list=test_points, close_surface=True, name="PL07_segmented_compound_line_closed")

###############################################################################
# The parameter ``cover_surface=True`` also performs the modeler command
# ``cover_surface``. Note that specifying ``cover_surface=True`` automatically
# results in the polyline being closed.

P = prim3D.create_polyline(position_list=test_points, cover_surface=True, name="SPL01_segmented_compound_line")

###############################################################################
# Compound lines
# --------------
# The following examples are for inserting compound lines.
#
# Insert line segment
# ~~~~~~~~~~~~~~~~~~~
# Insert a line segment starting at vertex 1 ``["100mm", "0mm", "0mm"]``
# of an existing polyline and ending at some new point ``["90mm", "20mm", "0mm"].``
# By numerical comparison of the starting point with the existing vertices of the
# original polyline object, it is determined automatically that the segment is
# inserted after the first segment of the original polyline.

P = prim3D.create_polyline(position_list=test_points, close_surface=True, name="PL08_segmented_compound_insert_segment")

p2 = P.points[1]
insert_point = ["-100mm", "20mm", "0mm"]

P.insert_segment(position_list=[insert_point, p2])

###############################################################################
# Insert compound line with insert curve
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Insert a compound line starting a line segment at vertex 1 ``["100mm", "0mm", "0mm"]``
# of an existing polyline and end at some new point ``["90mm", "20mm", "0mm"]``.
# By numerical comparison of the starting point, it is determined automatically
# that the segment is inserted after the first segment of the original polyline.

P = prim3D.create_polyline(position_list=test_points, close_surface=False, name="PL08_segmented_compound_insert_arc")

start_point = P.vertex_positions[1]
insert_point1 = ["90mm", "20mm", "0mm"]
insert_point2 = [40, 40, 0]

P.insert_segment(position_list=[start_point, insert_point1, insert_point2], segment="Arc")

###############################################################################
# Insert compound line at end of a center-point arc
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Insert a compound line at the end of a center-point arc (``type="AngularArc"``).
# This is a special case.
#
# Step 1: Draw a center-point arc.

start_point = [2200.0, 0.0, 1200.0]
arc_center_1 = [1400, 0, 800]
arc_angle_1 = "43.47deg"

P = prim3D.create_polyline(
    name="First_Arc",
    position_list=[start_point],
    segment_type=prim3D.polyline_segment(type="AngularArc", arc_angle=arc_angle_1, arc_center=arc_center_1),
)

###############################################################################
# Step 2: Insert a line segment at the end of the arc with a specified end point.

start_of_line_segment = P.end_point
end_of_line_segment = [3600, 200, 30]

P.insert_segment(position_list=[start_of_line_segment, end_of_line_segment])

###############################################################################
# Step 3: Append a center-point arc segment to the line object.

arc_angle_2 = "39.716deg"
arc_center_2 = [3400, 200, 3800]

P.insert_segment(
    position_list=[end_of_line_segment],
    segment=prim3D.polyline_segment(type="AngularArc", arc_center=arc_center_2, arc_angle=arc_angle_2),
)

###############################################################################
# You can use the compound polyline definition to complete all three steps in
# a single step.

prim3D.create_polyline(
    position_list=[start_point, end_of_line_segment],
    segment_type=[
        prim3D.polyline_segment(type="AngularArc", arc_angle="43.47deg", arc_center=arc_center_1),
        prim3D.polyline_segment(type="Line"),
        prim3D.polyline_segment(type="AngularArc", arc_angle=arc_angle_2, arc_center=arc_center_2),
    ],
    name="Compound_Polyline_One_Command",
)

#########################################################################
# Insert two 3-point arcs forming a circle and covered
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Insert two 3-point arcs forming a circle and covered.
# Note that the last point of the second arc segment is not defined in
# the position list.

P = prim3D.create_polyline(
    position_list=[[34.1004, 14.1248, 0], [27.646, 16.7984, 0], [24.9725, 10.3439, 0], [31.4269, 7.6704, 0]],
    segment_type=["Arc", "Arc"],
    cover_surface=True,
    close_surface=True,
    name="Rotor_Subtract_25_0",
    matname="vacuum",
)

###############################################################################
# Here is an example of a complex polyline where the number of points is
# insufficient to populate the requested segments. This results in an
# ``IndexError`` that PyAEDT catches silently. The return value of the command
# is ``False``, which can be caught at the app level.  While this example might
# not be so useful in a Jupyter Notebook, it is important for unit tests.

MDL_points = [
    ["67.1332mm", "2.9901mm", "0mm"],
    ["65.9357mm", "2.9116mm", "0mm"],
    ["65.9839mm", "1.4562mm", "0mm"],
    ["66mm", "0mm", "0mm"],
    ["99mm", "0mm", "0mm"],
    ["98.788mm", "6.4749mm", "0mm"],
    ["98.153mm", "12.9221mm", "0mm"],
    ["97.0977mm", "19.3139mm", "0mm"],
]


MDL_segments = ["Line", "Arc", "Line", "Arc", "Line"]
return_value = prim3D.create_polyline(MDL_points, segment_type=MDL_segments, name="MDL_Polyline")
assert return_value  # triggers an error at the application error

###############################################################################
# Here is an example that provides more points than the segment list requires.
# This is valid usage. The remaining points are ignored.

MDL_segments = ["Line", "Arc", "Line", "Arc"]

P = prim3D.create_polyline(MDL_points, segment_type=MDL_segments, name="MDL_Polyline")

###############################################################################
# Save project
# ------------
# Save the project.

project_dir = r"C:\temp"
project_name = "Polylines"
project_file = os.path.join(project_dir, project_name + ".aedt")

M3D.save_project(project_file)

M3D.release_desktop()
