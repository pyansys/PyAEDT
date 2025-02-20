"""
Maxwell 3D: bath plate analysis
-------------------------------
This example uses PyAEDT to set up the TEAM 3 bath plate problem and
solve it using the Maxwell 3D Eddy Current solver.
https://www.compumag.org/wp/wp-content/uploads/2018/06/problem3.pdf
"""
##################################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import pyaedt
import tempfile

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

###########################################################################################
# Create temporary directory
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create temporary directory.

temp_dir = tempfile.TemporaryDirectory(suffix=".ansys")

##################################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

##################################################################################
# Launch AEDT and Maxwell 3D
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT and Maxwell 3D after first setting up the project and design names,
# the solver, and the version. The following code also creates an instance of the
# ``Maxwell3d`` class named ``M3D``. 

project_name = "COMPUMAG"
design_name = "TEAM 3 Bath Plate"
solver = "EddyCurrent"

m3d = pyaedt.Maxwell3d(
    projectname=project_name,
    designname=design_name,
    solution_type=solver,
    specified_version=aedt_version,
    non_graphical=non_graphical,
    new_desktop_session=True,
)
m3d.modeler.model_units = "mm"

###############################################################################
# Add variable
# ~~~~~~~~~~~~
# Add a design variable named ``Coil_Position`` that you use later to adjust the
# position of the coil.

Coil_Position = -20
m3d["Coil_Position"] = str(Coil_Position) + m3d.modeler.model_units

################################################################################
# Add material
# ~~~~~~~~~~~~
# Add a material named ``team3_aluminium`` for the ladder plate.

mat = m3d.materials.add_material("team3_aluminium")
mat.conductivity = 32780000

###############################################################################
# Draw background region
# ~~~~~~~~~~~~~~~~~~~~~~
# Draw a background region that uses the default properties for an air region.

m3d.modeler.create_air_region(x_pos=100, y_pos=100, z_pos=100, x_neg=100, y_neg=100, z_neg=100)

################################################################################
# Draw ladder plate and assign material
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Draw a ladder plate and assign it the newly created material ``team3_aluminium``.

m3d.modeler.create_box(origin=[-30, -55, 0], sizes=[60, 110, -6.35], name="LadderPlate", material="team3_aluminium")
m3d.modeler.create_box(origin=[-20, -35, 0], sizes=[40, 30, -6.35], name="CutoutTool1")
m3d.modeler.create_box(origin=[-20, 5, 0], sizes=[40, 30, -6.35], name="CutoutTool2")
m3d.modeler.subtract("LadderPlate", ["CutoutTool1", "CutoutTool2"], keep_originals=False)

################################################################################
# Add mesh refinement to ladder plate
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Add a mesh refinement to the ladder plate.

m3d.mesh.assign_length_mesh("LadderPlate", maximum_length=3, maximum_elements=None, name="Ladder_Mesh")

################################################################################
# Draw search coil and assign excitation
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Draw a search coil and assign it a ``stranded`` current excitation. 
# The stranded type forces the current density to be constant in the coil.

m3d.modeler.create_cylinder(orientation="Z", origin=[0, "Coil_Position", 15], radius=40, height=20, name="SearchCoil",
                            material="copper")
m3d.modeler.create_cylinder(orientation="Z", origin=[0, "Coil_Position", 15], radius=20, height=20, name="Bore",
                            material="copper")
m3d.modeler.subtract("SearchCoil", "Bore", keep_originals=False)
m3d.modeler.section("SearchCoil", "YZ")
m3d.modeler.separate_bodies("SearchCoil_Section1")
m3d.modeler.delete("SearchCoil_Section1_Separate1")
m3d.assign_current(assignment=["SearchCoil_Section1"], amplitude=1260, solid=False, name="SearchCoil_Excitation")

################################################################################
# Draw a line for plotting Bz
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Draw a line for plotting Bz later. Bz is the Z component of the flux
# density. The following code also adds a small diameter cylinder to refine the
# mesh locally around the line.

line_points = [["0mm", "-55mm", "0.5mm"], ["0mm", "55mm", "0.5mm"]]
m3d.modeler.create_polyline(points=line_points, name="Line_AB")
poly = m3d.modeler.create_polyline(points=line_points, name="Line_AB_MeshRefinement")
poly.set_crosssection_properties(type="Circle", width="0.5mm")

###############################################################################
# Plot model
# ~~~~~~~~~~
# Plot the model.

m3d.plot(show=False, export_path=os.path.join(temp_dir.name, "Image.jpg"), plot_air_objects=False)

###############################################################################
# Add Maxwell 3D setup
# ~~~~~~~~~~~~~~~~~~~~
# Add a Maxwell 3D setup with frequency points at 50 Hz and 200 Hz.

setup = m3d.create_setup(name="Setup1")
setup.props["Frequency"] = "200Hz"
setup.props["HasSweepSetup"] = True
setup.add_eddy_current_sweep(range_type="LinearStep", start=50, end=200, count=150, clear=True)

################################################################################
# Adjust eddy effects
# ~~~~~~~~~~~~~~~~~~~
# Adjust eddy effects for the ladder plate and the search coil. The setting for
# eddy effect is ignored for the stranded conductor type used in the search coil.

m3d.eddy_effects_on(assignment=["LadderPlate"], enable_eddy_effects=True, enable_displacement_current=True)
m3d.eddy_effects_on(assignment=["SearchCoil"], enable_eddy_effects=False, enable_displacement_current=True)

################################################################################
# Add linear parametric sweep
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Add a linear parametric sweep for the two coil positions.

sweep_name = "CoilSweep"
param = m3d.parametrics.add("Coil_Position", -20, 0, 20, "LinearStep", parametricname=sweep_name)
param["SaveFields"] = True
param["CopyMesh"] = False
param["SolveWithCopiedMeshOnly"] = True

################################################################################
# Solve parametric sweep
# ~~~~~~~~~~~~~~~~~~~~~~
# Solve the parametric sweep directly so that results of all variations are available.

m3d.analyze_setup(sweep_name)

###############################################################################
# Create expression for Bz
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Create an expression for Bz using the fields calculator.

Fields = m3d.ofieldsreporter
Fields.EnterQty("B")
Fields.CalcOp("ScalarZ")
Fields.EnterScalar(1000)
Fields.CalcOp("*")
Fields.CalcOp("Smooth")
Fields.AddNamedExpression("Bz", "Fields")

###############################################################################
# Plot mag(Bz) as a function of frequency
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Plot mag(Bz) as a function of frequency for both coil positions.

variations = {"Distance": ["All"], "Freq": ["All"], "Phase": ["0deg"], "Coil_Position": ["All"]}
m3d.post.create_report(expressions="mag(Bz)", variations=variations, primary_sweep_variable="Distance",
                       report_category="Fields", context="Line_AB", plot_name="mag(Bz) Along 'Line_AB' Coil")

###############################################################################
# Get simulation results from a solved setup
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get simulation results from a solved setup as a ``SolutionData`` object.

solutions = m3d.post.get_solution_data(
    expressions="mag(Bz)",
    report_category="Fields",
    context="Line_AB",
    variations=variations,
    primary_sweep_variable="Distance",
)

###############################################################################
# Set up sweep value and plot solution
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Set up a sweep value and plot the solution.

solutions.active_variation["Coil_Position"] = -0.02
solutions.plot()

###############################################################################
# Change sweep value and plot solution
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Change the sweep value and plot the solution again.

solutions.active_variation["Coil_Position"] = 0
solutions.plot()

###############################################################################
# Plot induced current density on surface of ladder plate
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Plot the induced current density, ``"Mag_J"``, on the surface of the ladder plate.

ladder_plate = m3d.modeler.objects_by_name["LadderPlate"]
intrinsic_dict = {"Freq": "50Hz", "Phase": "0deg"}
m3d.post.create_fieldplot_surface(ladder_plate.faces, "Mag_J", intrinsics=intrinsic_dict, plot_name="Mag_J")

###############################################################################
# Release AEDT
# ~~~~~~~~~~~~
# Release AEDT from the script engine, leaving both AEDT and the project open.

m3d.release_desktop(False, False)
temp_dir.cleanup()
