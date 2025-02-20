"""
Transformer leakage inductance calculation in Maxwell 2D Magnetostatic
----------------------------------------------------------------------
This example shows how you can use pyAEDT to create a Maxwell 2D
magnetostatic analysis to calculate transformer leakage
inductance and reactance.
The analysis based on this document form page 8 on:
https://www.ee.iitb.ac.in/~fclab/FEM/FEM1.pdf
"""

##########################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~

import tempfile
from pyaedt import Maxwell2d

temp_dir = tempfile.TemporaryDirectory(suffix=".ansys")

##################################
# Initialize and launch Maxwell 2D
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Initialize and launch Maxwell 2D, providing the version, path to the project, and the design
# name and type.

non_graphical = False

project_name = "Transformer_leakage_inductance"
design_name = "1 Magnetostatic"
solver = "MagnetostaticXY"
desktop_version = "2024.1"

m2d = Maxwell2d(specified_version=desktop_version,
                new_desktop_session=False,
                designname=design_name,
                projectname=project_name,
                solution_type=solver,
                non_graphical=non_graphical)

#########################
# Initialize dictionaries
# ~~~~~~~~~~~~~~~~~~~~~~~
# Initialize dictionaries that contain all the definitions for the design variables.

mod = m2d.modeler
mod.model_units = "mm"

dimensions = {
    "core_width": "1097mm",
    "core_height": "2880mm",
    "core_opening_x1": "270mm",
    "core_opening_x2": "557mm",
    "core_opening_y1": "540mm",
    "core_opening_y2": "2340mm",
    "core_opening_width": "core_opening_x2-core_opening_x1",
    "core_opening_height": "core_opening_y2-core_opening_y1",
    "LV_x1": "293mm",
    "LV_x2": "345mm",
    "LV_width": "LV_x2-LV_x1",
    "LV_mean_radius": "LV_x1+LV_width/2",
    "LV_mean_turn_length": "pi*2*LV_mean_radius",
    "LV_y1": "620mm",
    "LV_y2": "2140mm",
    "LV_height": "LV_y2-LV_y1",
    "HV_x1": "394mm",
    "HV_x2": "459mm",
    "HV_width": "HV_x2-HV_x1",
    "HV_mean_radius": "HV_x1+HV_width/2",
    "HV_mean_turn_length": "pi*2*HV_mean_radius",
    "HV_y1": "620mm",
    "HV_y2": "2140mm",
    "HV_height": "HV_y2-HV_y1",
    "HV_LV_gap_radius": "(LV_x2 + HV_x1)/2",
    "HV_LV_gap_length": "pi*2*HV_LV_gap_radius",
}

specifications = {
    "Amp_turns": "135024A",
    "Frequency": "50Hz",
    "HV_turns": "980",
    "HV_current": "Amp_turns/HV_turns",
}

####################################
# Define variables from dictionaries
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Define design variables from the created dictionaries.

m2d.variable_manager.set_variable(variable_name="Dimensions")

for k, v in dimensions.items():
    m2d[k] = v

m2d.variable_manager.set_variable(variable_name="Windings")

for k, v in specifications.items():
    m2d[k] = v

##########################
# Create design geometries
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Create transformer core, HV and LV windings, and the region.

core_id = mod.create_rectangle(
    position=[0, 0, 0],
    dimension_list=["core_width", "core_height", 0],
    name="core",
    matname="steel_1008",
)

core_hole_id = mod.create_rectangle(
    position=["core_opening_x1", "core_opening_y1", 0],
    dimension_list=["core_opening_width", "core_opening_height", 0],
    name="core_hole",
)

mod.subtract(blank_list=[core_id], tool_list=[core_hole_id], keep_originals=False)

lv_id = mod.create_rectangle(
    position=["LV_x1", "LV_y1", 0],
    dimension_list=["LV_width", "LV_height", 0],
    name="LV",
    matname="copper",
)

hv_id = mod.create_rectangle(
    position=["HV_x1", "HV_y1", 0],
    dimension_list=["HV_width", "HV_height", 0],
    name="HV",
    matname="copper",
)

# Very small region is enough, because all the flux is concentrated in the core
region_id = mod.create_region(
    pad_percent=[20, 10, 0, 10]
)

###########################
# Assign boundary condition
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Assign vector potential to zero on all region boundaries. This makes x=0 edge a symmetry boundary.

region_edges = region_id.edges

m2d.assign_vector_potential(
    input_edge=region_edges,
    bound_name="VectorPotential1"
)

##############################
# Create initial mesh settings
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Assign a relatively dense mesh to all objects to ensure that the energy is calculated accurately.

m2d.mesh.assign_length_mesh(
    names=["core", "Region", "LV", "HV"],
    maxlength=50,
    maxel=None,
    meshop_name="all_objects"
)

####################
# Define excitations
# ~~~~~~~~~~~~~~~~~~
# Assign the same current in amp-turns but in opposite directions to HV and LV windings.

m2d.assign_current(
    object_list=lv_id,
    amplitude="Amp_turns",
    name="LV"
)
m2d.assign_current(
    object_list=hv_id,
    amplitude="Amp_turns",
    name="HV",
    swap_direction=True
)

##############################
# Create and analyze the setup
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create and analyze the setup. Setu no. of minimum passes to 3 to ensure accuracy.

m2d.create_setup(
    setupname="Setup1",
    MinimumPasses=3
)
m2d.analyze_setup()


########################################################
# Calculate transformer leakage inductance and reactance
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Calculate transformer leakage inductance from the magnetic energy.

field_calculator = m2d.ofieldsreporter

field_calculator.EnterQty("Energy")
field_calculator.EnterSurf("HV")
field_calculator.CalcOp("Integrate")
field_calculator.EnterScalarFunc("HV_mean_turn_length")
field_calculator.CalcOp("*")

field_calculator.EnterQty("Energy")
field_calculator.EnterSurf("LV")
field_calculator.CalcOp("Integrate")
field_calculator.EnterScalarFunc("LV_mean_turn_length")
field_calculator.CalcOp("*")

field_calculator.EnterQty("Energy")
field_calculator.EnterSurf("Region")
field_calculator.CalcOp("Integrate")
field_calculator.EnterScalarFunc("HV_LV_gap_length")
field_calculator.CalcOp("*")

field_calculator.CalcOp("+")
field_calculator.CalcOp("+")

field_calculator.EnterScalar(2)
field_calculator.CalcOp("*")
field_calculator.EnterScalarFunc("HV_current")
field_calculator.EnterScalarFunc("HV_current")
field_calculator.CalcOp("*")
field_calculator.CalcOp("/")
field_calculator.AddNamedExpression("Leakage_inductance", "Fields")

field_calculator.CopyNamedExprToStack("Leakage_inductance")
field_calculator.EnterScalar(2)
field_calculator.EnterScalar(3.14159265358979)
field_calculator.EnterScalarFunc("Frequency")
field_calculator.CalcOp("*")
field_calculator.CalcOp("*")
field_calculator.CalcOp("*")
field_calculator.AddNamedExpression("Leakage_reactance", "Fields")

m2d.post.create_report(
    expressions=["Leakage_inductance", "Leakage_reactance"],
    report_category="Fields",
    primary_sweep_variable="core_width",
    plot_type="Data Table",
    plotname="Transformer Leakage Inductance",
)

######################################################################
# Print leakage inductance and reactance values in the Message Manager
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Print leakage inductance and reactance values in the Message Manager

m2d.logger.clear_messages()
m2d.logger.info(
    "Leakage_inductance =  {:.4f}H".format(m2d.post.get_scalar_field_value(quantity_name="Leakage_inductance"))
)
m2d.logger.info(
    "Leakage_reactance =  {:.2f}Ohm".format(m2d.post.get_scalar_field_value(quantity_name="Leakage_reactance"))
)

######################################
# Plot energy in the simulation domain
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Most of the energy is confined in the air between the HV and LV windings.

object_faces = []
for name in mod.object_names:
    object_faces.extend(m2d.modeler.get_object_faces(name))

energy_field_overlay = m2d.post.create_fieldplot_surface(
    objlist=object_faces,
    quantityName="energy",
    plot_name="Energy",
)

m2d.save_project()
m2d.release_desktop()
temp_dir.cleanup()
