"""
Maxwell 3D: asymmetric conductor analysis
-----------------------------------------
This example uses PyAEDT to set up the TEAM 7 problem for an asymetric
conductor with a hole and solve it using the Maxwell 3D Eddy Current solver.
"""
###########################################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

from pyaedt import Maxwell3d
from pyaedt import generate_unique_project_name
import numpy as np
import csv
import os

###########################################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

###########################################################################################
# Launch AEDT and Maxwell 3D
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT and Maxwell 3D. The following code sets up the project and design names, the solver, and
# the version. It also creates an instance of the ``Maxwell3d`` class named ``M3D``. 

Project_Name = "COMPUMAG"
Design_Name = "TEAM 7 Asymmetric Conductor"
Solver = "EddyCurrent"
DesktopVersion = "2023.2"

M3D = Maxwell3d(
    projectname=generate_unique_project_name(),
    designname=Design_Name,
    solution_type=Solver,
    specified_version=DesktopVersion,
    non_graphical=non_graphical,
    new_desktop_session=True
)
M3D.modeler.model_units = "mm"
modeler = M3D.modeler
Plot = M3D.odesign.GetModule("ReportSetup")

###########################################################################################
# Add Maxwell 3D setup
# ~~~~~~~~~~~~~~~~~~~~
# Add a Maxwell 3D setup with frequency points at DC, 50 Hz, and 200Hz.
# Otherwise, the default PyAEDT setup values are used. To approximate a DC field in the
# Eddy Current solver, use a low frequency value. Second-order shape functions improve
# the smoothness of the induced currents in the plate.

dc_freq = 0.1
stop_freq = 50

Setup = M3D.create_setup(setupname="Setup1")
Setup.props["Frequency"] = "200Hz"
Setup.props["HasSweepSetup"] = True
Setup.add_eddy_current_sweep("LinearStep", dc_freq, stop_freq, stop_freq - dc_freq, clear=True)
Setup.props["UseHighOrderShapeFunc"] = True
Setup.props["PercentError"] = 0.4

###########################################################################################
# Define coil dimensions
# ~~~~~~~~~~~~~~~~~~~~~~
# Define coil dimensions as shown on the TEAM7 drawing of the coil.

coil_external = 150 + 25 + 25
coil_internal = 150
coil_r1 = 25
coil_r2 = 50
coil_thk = coil_r2 - coil_r1
coil_height = 100
coil_centre = [294 - 25 - 150 / 2, 25 + 150 / 2, 19 + 30 + 100 / 2]

# Use expressions to construct the three dimensions needed to describe the midpoints of
# the coil.

dim1 = coil_internal / 2 + (coil_external - coil_internal) / 4
dim2 = coil_internal / 2 - coil_r1
dim3 = dim2 + np.sqrt(((coil_r1 + (coil_r2 - coil_r1) / 2) ** 2) / 2)

# Use coordinates to draw a polyline along which to sweep the coil cross sections.
P1 = [dim1, -dim2, 0]
P2 = [dim1, dim2, 0]
P3 = [dim3, dim3, 0]
P4 = [dim2, dim1, 0]

###########################################################################################
# Create coordinate system for positioning coil
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a coordinate system for positioning the coil.

M3D.modeler.create_coordinate_system(origin=coil_centre, mode="view", view="XY", name="Coil_CS")

###########################################################################################
# Create polyline
# ~~~~~~~~~~~~~~~
# Create a polyline. One quarter of the coil is modeled by sweeping a 2D sheet along a polyline.

test = M3D.modeler.create_polyline(position_list=[P1, P2, P3, P4], segment_type=["Line", "Arc"], name="Coil")
test.set_crosssection_properties(type="Rectangle", width=coil_thk, height=coil_height)

###########################################################################################
# Duplicate and unite polyline to create full coil
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Duplicate and unit the polyline to create a full coil.

M3D.modeler.duplicate_around_axis(
    "Coil", cs_axis="Global", angle=90, nclones=4, create_new_objects=True, is_3d_comp=False
)
M3D.modeler.unite("Coil,Coil_1,Coil_2")
M3D.modeler.unite("Coil,Coil_3")
M3D.modeler.fit_all()

###########################################################################################
# Assign material and if solution is allowed inside coil
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Assign the material ``Cooper`` from the Maxwell internal library to the coil and
# allow a solution inside the coil.

M3D.assign_material("Coil", "Copper")
M3D.solve_inside("Coil")

###########################################################################################
# Create terminal
# ~~~~~~~~~~~~~~~
# Create a terminal for the coil from a cross section that is split and one half deleted.

M3D.modeler.section("Coil", "YZ")
M3D.modeler.separate_bodies("Coil_Section1")
M3D.modeler.delete("Coil_Section1_Separate1")

# Add variable for coil excitation
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Add a design variable for coil excitation. The NB units here are AmpereTurns.

Coil_Excitation = 2742
M3D["Coil_Excitation"] = str(Coil_Excitation) + "A"
M3D.assign_current("Coil_Section1", amplitude="Coil_Excitation", solid=False)
M3D.modeler.set_working_coordinate_system("Global")

###########################################################################################
# Add a material
# ~~~~~~~~~~~~~~
# Add a material named ``team3_aluminium``.

mat = M3D.materials.add_material("team7_aluminium")
mat.conductivity = 3.526e7

###########################################################################################
# Model aluminium plate with a hole
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Model the aluminium plate with a hole by subtracting two rectangular cuboids.

plate = M3D.modeler.create_box(position=[0, 0, 0], dimensions_list=[294, 294, 19], name="Plate",
                               matname="team7_aluminium")
M3D.modeler.fit_all()
hole = M3D.modeler.create_box(position=[18, 18, 0], dimensions_list=[108, 108, 19], name="Hole")
M3D.modeler.subtract("Plate", ["Hole"], keep_originals=False)

###########################################################################################
# Draw a background region
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Draw a background region that uses the default properties for an air region.

M3D.modeler.create_air_region(x_pos=100, y_pos=100, z_pos=100, x_neg=100, y_neg=100, z_neg=100)

################################################################################
# Adjust eddy effects for plate and coil
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Adjust the eddy effects for the plate and coil by turning off displacement currents
# for all parts. The setting for eddy effect is ignored for the stranded conductor type
# used in the coil.

M3D.eddy_effects_on(object_list="Plate")
M3D.eddy_effects_on(object_list=["Coil", "Region", "Line_A1_B1mesh", "Line_A2_B2mesh"],
                    activate_eddy_effects=False,
                    activate_displacement_current=False)

################################################################################
# Create expression for Z component of B in Gauss
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create an expression for the Z component of B in Gauss using the fields calculator.

Fields = M3D.odesign.GetModule("FieldsReporter")
Fields.EnterQty("B")
Fields.CalcOp("ScalarZ")
Fields.EnterScalarFunc("Phase")
Fields.CalcOp("AtPhase")
Fields.EnterScalar(10000)
Fields.CalcOp("*")
Fields.CalcOp("Smooth")
Fields.AddNamedExpression("Bz", "Fields")

################################################################################
# Draw two lines along which to plot Bz
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Draw two lines along which to plot Bz. The following code also adds a small cylinder
# to refine the mesh locally around each line.

lines = ["Line_A1_B1", "Line_A2_B2"]
mesh_diameter = "2mm"

line_points_1 = [["0mm", "72mm", "34mm"], ["288mm", "72mm", "34mm"]]
polyline = modeler.create_polyline(position_list=line_points_1, name=lines[0])
L1Mesh = modeler.create_polyline(position_list=line_points_1, name=lines[0] + "mesh")
L1Mesh.set_crosssection_properties(type="Circle", width=mesh_diameter)

line_points_2 = [["0mm", "144mm", "34mm"], ["288mm", "144mm", "34mm"]]
polyline2 = modeler.create_polyline(position_list=line_points_2, name=lines[1])
polyline2_mesh = modeler.create_polyline(position_list=line_points_2, name=lines[1] + "mesh")
polyline2_mesh.set_crosssection_properties(type="Circle", width=mesh_diameter)

###############################################################################
# Plot model
# ~~~~~~~~~~
# Plot the model.

M3D.plot(show=False, export_path=os.path.join(M3D.working_directory, "Image.jpg"), plot_air_objects=False)

################################################################################
# Published measurement results are included with this script via the list below.
# Test results are used to create text files for import into a rectangular plot
# and to overlay simulation results.

project_dir = M3D.working_directory
dataset = [
    "Bz A1_B1 000 0",
    "Bz A1_B1 050 0",
    "Bz A1_B1 050 90",
    "Bz A1_B1 200 0",
    "Bz A1_B1 200 90",
    "Bz A2_B2 050 0",
    "Bz A2_B2 050 90",
    "Bz A2_B2 200 0",
    "Bz A2_B2 200 90",
]
header = ["Distance [mm]", "Bz [Tesla]"]

line_length = [0, 18, 36, 54, 72, 90, 108, 126, 144, 162, 180, 198, 216, 234, 252, 270, 288]
data = [
    [
        -6.667,
        -7.764,
        -8.707,
        -8.812,
        -5.870,
        8.713,
        50.40,
        88.47,
        100.9,
        104.0,
        104.8,
        104.9,
        104.6,
        103.1,
        97.32,
        75.19,
        29.04,
    ],
    [
        4.90,
        -17.88,
        -22.13,
        -20.19,
        -15.67,
        0.36,
        43.64,
        78.11,
        71.55,
        60.44,
        53.91,
        52.62,
        53.81,
        56.91,
        59.24,
        52.78,
        27.61,
    ],
    [-1.16, 2.84, 4.15, 4.00, 3.07, 2.31, 1.89, 4.97, 12.61, 14.15, 13.04, 12.40, 12.05, 12.27, 12.66, 9.96, 2.36],
    [
        -3.63,
        -18.46,
        -23.62,
        -21.59,
        -16.09,
        0.23,
        44.35,
        75.53,
        63.42,
        53.20,
        48.66,
        47.31,
        48.31,
        51.26,
        53.61,
        46.11,
        24.96,
    ],
    [-1.38, 1.20, 2.15, 1.63, 1.10, 0.27, -2.28, -1.40, 4.17, 3.94, 4.86, 4.09, 3.69, 4.60, 3.48, 4.10, 0.98],
    [
        -1.83,
        -8.50,
        -13.60,
        -15.21,
        -14.48,
        -5.62,
        28.77,
        60.34,
        61.84,
        56.64,
        53.40,
        52.36,
        53.93,
        56.82,
        59.48,
        52.08,
        26.56,
    ],
    [-1.63, -0.60, -0.43, 0.11, 1.26, 3.40, 6.53, 10.25, 11.83, 11.83, 11.01, 10.58, 10.80, 10.54, 10.62, 9.03, 1.79],
    [
        -0.86,
        -7.00,
        -11.58,
        -13.36,
        -13.77,
        -6.74,
        24.63,
        53.19,
        54.89,
        50.72,
        48.03,
        47.13,
        48.25,
        51.35,
        53.35,
        45.37,
        24.01,
    ],
    [-1.35, -0.71, -0.81, -0.67, 0.15, 1.39, 2.67, 3.00, 4.01, 3.80, 4.00, 3.02, 2.20, 2.78, 1.58, 1.37, 0.93],
]

# Dataset details are used to encode test parameters in the text files.
# For example, ``Bz A1_B1 050 0`` is the Z component of flux density ``B``
# along line ``A1_B1`` at 50 Hz and 0 deg. These text files are created
# and saved in the default project directory.

print("project_dir", project_dir)
dataset_range = range(int(0), len(dataset), int(1))
line_length_range = range(int(0), len(line_length), int(1))
dataset_list = []

for item in dataset_range:
    dataset_list.clear()
    for jtem in line_length_range:
        dataset_list.insert(jtem, data[item][jtem])
        ziplist = zip(line_length, dataset_list)
    with open(project_dir + "\\" + str(dataset[item]) + ".csv", "w", newline="") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(header)
        writer.writerows(ziplist)

# Create rectangular plots
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Create rectangular plots, using text file encoding to control their formatting. Create
# the DC plot separately because it needs a different frequency and phase than the other plots.

for item in dataset_range:
    if item % 2 == 0:
        plotname = dataset[item][0:3] + "Along the Line" + dataset[item][2:9] + ", " + dataset[item][9:12] + "Hz"
        if dataset[item][9:12] == "000":
            variations = {
                "Distance": ["All"],
                "Freq": [str(dc_freq) + "Hz"],
                "Phase": ["0deg"],
                "Coil_Excitation": ["All"],
            }
            M3D.post.create_report(
                plotname=plotname,
                report_category="Fields",
                context="Line_" + dataset[item][3:8],
                primary_sweep_variable="Distance",
                variations=variations,
                expressions=dataset[item][0:2],
            )
        else:
            variations = {
                "Distance": ["All"],
                "Freq": [dataset[item][9:12] + "Hz"],
                "Phase": ["0deg", "90deg"],
                "Coil_Excitation": ["All"],
            }
            M3D.post.create_report(
                plotname=plotname,
                report_category="Fields",
                context="Line_" + dataset[item][3:8],
                primary_sweep_variable="Distance",
                variations=variations,
                expressions=dataset[item][0:2],
            )

# Import test data into correct plot and overlay with simulation results
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Import test data into the correct plot and overlay it with the simulation results.

if item == 0:
    Plot.ImportIntoReport(plotname, os.path.join(project_dir, str(dataset[item]) + ".csv"))
else:
    Plot.ImportIntoReport(plotname, project_dir + "\\" + str(dataset[item - 1]) + ".csv")
    Plot.ImportIntoReport(plotname, project_dir + "\\" + str(dataset[item]) + ".csv")

###################################################################################################
# Create plots of induced current and flux density on surface of plate
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create two plots of the induced current (``Mag_J``) and the flux density (``Mag_B``) on the
# surface of the plate.

surflist = modeler.get_object_faces("Plate")
intrinsic_dict = {"Freq": "200Hz", "Phase": "0deg"}
M3D.post.create_fieldplot_surface(surflist, "Mag_J", intrinsincDict=intrinsic_dict, plot_name="Mag_J")
M3D.post.create_fieldplot_surface(surflist, "Mag_B", intrinsincDict=intrinsic_dict, plot_name="Mag_B")

###################################################################################################
# Save project and solve
# ~~~~~~~~~~~~~~~~~~~~~~
# Save the project and solve it.

M3D.save_project()
M3D.analyze()

####################################################################################################
# Release AEDT from PyAEDT scripting
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Release AEDT from PyAEDT scripting. If you wanted to leave AEDT and the project open
# after running the above script, in the following command, you would set ``(False, False)``.

M3D.release_desktop(True, True)
