"""
Q2D: Cable parameter identification
---------------------------------------------------
This example shows how you can use PyAEDT to perform these tasks:

 - Create a Q2D design using the Modeler primitives and importing part of the geometry.
 - Set up the entire simulation.
 - Link the solution to a Simplorer design.

 For cable information, see `4 Core Armoured Power Cable <https://www.luxingcable.com/low-voltage-cables/4-core-armoured-power-cable.html>`_

"""
#################################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~

import pyaedt
import math

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

#################################################################################
# Initialize core strand dimensions and positions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Initialize cable sizing - radii in mm.

c_strand_radius = 2.575
cable_n_cores = 4
core_n_strands = 6
core_xlpe_ins_thickness = 0.5
core_xy_coord = math.ceil(3 * c_strand_radius + 2 * core_xlpe_ins_thickness)

#################################################################################
# Initialize filling and sheath dimensions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Initialize radii of further structures incrementally adding thicknesses.

filling_radius = 1.4142 * (core_xy_coord + 3 * c_strand_radius + core_xlpe_ins_thickness + 0.5)
inner_sheath_radius = filling_radius + 0.75
armour_thickness = 3
armour_radius = inner_sheath_radius + armour_thickness
outer_sheath_radius = armour_radius + 2

#################################################################################
# Initialize armature strand dimensions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Initialize radii.

armour_centre_pos = inner_sheath_radius + armour_thickness / 2.0
arm_strand_rad = armour_thickness / 2.0 - 0.2
n_arm_strands = 30

#################################################################################
# Initialize dictionaries
# ~~~~~~~~~~~~~~~~~~~~~~~
# Initialize dictionaries that contain all the definitions for the design
# variables and output variables.

core_params = {
    "n_cores": str(cable_n_cores),
    "n_strands_core": str(core_n_strands),
    "c_strand_radius": str(c_strand_radius) + 'mm',
    "c_strand_xy_coord": str(core_xy_coord) + 'mm'
}
outer_params = {
    "filling_radius": str(filling_radius) + 'mm',
    "inner_sheath_radius": str(inner_sheath_radius) + 'mm',
    "armour_radius": str(armour_radius) + 'mm',
    "outer_sheath_radius": str(outer_sheath_radius) + 'mm'
}
armour_params = {
    "armour_centre_pos": str(armour_centre_pos) + 'mm',
    "arm_strand_rad": str(arm_strand_rad) + 'mm',
    "n_arm_strands": str(n_arm_strands)
}

#################################################################################
# Initialize Q2D
# ~~~~~~~~~~~~~~
# Initialize Q2D, providing the version, path to the project, and the design
# name and type.

project_name = 'Q2D_ArmouredCableExample'
q2d_design_name = '2D_Extractor_Cable'
setup_name = "MySetupAuto"
sweep_name = "sweep1"
tb_design_name = 'CableSystem'
q2d = pyaedt.Q2d(projectname=project_name, designname=q2d_design_name, specified_version=aedt_version)

##########################################################
# Define variables from dictionaries
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Define design variables from the created dictionaries.

for k, v in core_params.items():
    q2d[k] = v
for k, v in outer_params.items():
    q2d[k] = v
for k, v in armour_params.items():
    q2d[k] = v

##########################################################
# Create object to access 2D modeler
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create the ``mod2D`` object to access the 2D modeler easily.

mod2D = q2d.modeler
mod2D.delete()
mod2D.model_units = "mm"

#################################################################################
# Initialize required material properties
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Cable insulators require the definition of specific materials since they are not included in the Sys Library.
# Plastic, PE (cross-linked, wire, and cable grade)

mat_pe_cable_grade = q2d.materials.add_material("plastic_pe_cable_grade")
mat_pe_cable_grade.conductivity = "1.40573e-16"
mat_pe_cable_grade.permittivity = "2.09762"
mat_pe_cable_grade.dielectric_loss_tangent = "0.000264575"
mat_pe_cable_grade.update()
# Plastic, PP (10% carbon fiber)
mat_pp = q2d.materials.add_material("plastic_pp_carbon_fiber")
mat_pp.conductivity = "0.0003161"
mat_pp.update()

#####################################################################################
# Create geometry for core strands, filling, and XLPE insulation
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

mod2D.create_coordinate_system(['c_strand_xy_coord', 'c_strand_xy_coord', '0mm'], name='CS_c_strand_1')
mod2D.set_working_coordinate_system('CS_c_strand_1')
c1_id = mod2D.create_circle(['0mm', '0mm', '0mm'], 'c_strand_radius', name='c_strand_1', material='copper')
c2_id = c1_id.duplicate_along_line(vector=['0mm', '2.0*c_strand_radius', '0mm'], nclones=2)
mod2D.duplicate_around_axis(c2_id, axis="Z", angle=360 / core_n_strands, clones=6)
c_unite_name = mod2D.unite(q2d.get_all_conductors_names())

fill_id = mod2D.create_circle(['0mm', '0mm', '0mm'], '3*c_strand_radius', name='c_strand_fill',
                              material='plastic_pp_carbon_fiber')
fill_id.color = (255, 255, 0)
xlpe_id = mod2D.create_circle(['0mm', '0mm', '0mm'], '3*c_strand_radius+' + str(core_xlpe_ins_thickness) + 'mm',
                              name='c_strand_xlpe',
                              material='plastic_pe_cable_grade')
xlpe_id.color = (0, 128, 128)

mod2D.set_working_coordinate_system('Global')
all_obj_names = q2d.get_all_conductors_names() + q2d.get_all_dielectrics_names()
mod2D.duplicate_around_axis(all_obj_names, axis="Z", angle=360 / cable_n_cores, clones=4)
cond_names = q2d.get_all_conductors_names()

#####################################################################################
# Create geometry for filling object
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

filling_id = mod2D.create_circle(['0mm', '0mm', '0mm'], 'filling_radius', name='Filling',
                                 material='plastic_pp_carbon_fiber')
filling_id.color = (255, 255, 180)

#####################################################################################
# Create geometry for inner sheath object
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

inner_sheath_id = mod2D.create_circle(['0mm', '0mm', '0mm'], 'inner_sheath_radius', name='InnerSheath',
                                     material='PVC plastic')
inner_sheath_id.color = (0, 0, 0)

#####################################################################################
# Create geometry for armature fill
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

arm_fill_id = mod2D.create_circle(['0mm', '0mm', '0mm'], 'armour_radius', name='ArmourFilling',
                                  material='plastic_pp_carbon_fiber')
arm_fill_id.color = (255, 255, 255)

#####################################################################################
# Create geometry for outer sheath
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

outer_sheath_id = mod2D.create_circle(['0mm', '0mm', '0mm'], 'outer_sheath_radius', name='OuterSheath',
                                     material='PVC plastic')
outer_sheath_id.color = (0, 0, 0)

#####################################################################################
# Create geometry for armature steel strands
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

arm_strand_1_id = mod2D.create_circle(['0mm', 'armour_centre_pos', '0mm'], '1.1mm', name='arm_strand_1',
                                      material='steel_stainless')
arm_strand_1_id.color = (128, 128, 64)
arm_strand_1_id.duplicate_around_axis('Z', '360deg/n_arm_strands', clones='n_arm_strands')
arm_strand_names = mod2D.get_objects_w_string('arm_strand')

#####################################################################################
# Create region
# ~~~~~~~~~~~~~

region = q2d.modeler.create_region([500, 500, 500, 500])
region.material_name = "vacuum"

##########################################################
# Assign conductors and reference ground
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

obj = [q2d.modeler.get_object_from_name(i) for i in cond_names]
[q2d.assign_single_conductor(assignment=i, name='C1' + str(obj.index(i) + 1), conductor_type='SignalLine') for i
 in obj]
obj = [q2d.modeler.get_object_from_name(i) for i in arm_strand_names]
q2d.assign_single_conductor(assignment=obj, name="gnd", conductor_type="ReferenceGround")
mod2D.fit_all()

##########################################################
# Assign design settings
# ~~~~~~~~~~~~~~~~~~~~~~

lumped_length = "100m"
q2d_des_settings = q2d.design_settings
q2d_des_settings['LumpedLength'] = lumped_length

##########################################################
# Insert setup and frequency sweep
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

q2d_setup = q2d.create_setup(name=setup_name)
q2d_sweep = q2d_setup.add_sweep(name=sweep_name)

##########################################################
# Analyze setup
# ~~~~~~~~~~~~~

# q2d.analyze(setup_name=setup_name)

###################################################################
# Add a Simplorer/Twin Builder design and the Q3D dynamic component
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

tb = pyaedt.TwinBuilder(designname=tb_design_name)

##########################################################
# Add a Q3D dynamic component
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~

tb.add_q3d_dynamic_component(project_name, q2d_design_name, setup_name, sweep_name, coupling_matrix_name="Original",
                             model_depth=lumped_length)

##########################################################
# Save project and release desktop
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

tb.save_project()
tb.release_desktop(True, True)
