"""
Icepak: setup from Sherlock inputs
-----------------------------------
This example shows how you can create an Icepak project from Sherlock
files (STEP and CSV) and an AEDB board.
"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports and set paths.

import time
import os
import ansys.aedt.core
import datetime

# Set paths
project_folder = ansys.aedt.core.generate_unique_folder_name()
input_dir = ansys.aedt.core.downloads.download_sherlock(destination=project_folder)

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.2"

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` value either to ``True`` or ``False``.

non_graphical = False

###############################################################################
# Define variables
# ~~~~~~~~~~~~~~~~
# Define input variables. The following code creates all input variables that are needed
# to run this example.

material_name = "MaterialExport.csv"
component_properties = "TutorialBoardPartsList.csv"
component_step = "TutorialBoard.stp"
aedt_odb_project = "SherlockTutorial.aedt"
aedt_odb_design_name = "PCB"

###############################################################################
# Launch AEDT
# ~~~~~~~~~~~
# Launch AEDT 2024 R2 in graphical mode.

d = ansys.aedt.core.launch_desktop(version=aedt_version, non_graphical=non_graphical, new_desktop=True)

start = time.time()
material_list = os.path.join(input_dir, material_name)
component_list = os.path.join(input_dir, component_properties)
validation = os.path.join(project_folder, "validation.log")
file_path = os.path.join(input_dir, component_step)
project_name = os.path.join(project_folder, component_step[:-3] + "aedt")
component_name = "from_ODB"

###############################################################################
# Create Icepak project
# ~~~~~~~~~~~~~~~~~~~~~
# Create an Icepak project.

ipk = ansys.aedt.core.Icepak(project=project_name)

###############################################################################
# Disable autosave to speed up import
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Disable autosave to speed up the import.

d.disable_autosave()

###############################################################################
# Import PCB from AEDB file
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Import a PCB from an AEDB file.

odb_path = os.path.join(input_dir, aedt_odb_project)
ipk.create_pcb_from_3dlayout(component_name=component_name, project_name=odb_path, design_name=aedt_odb_design_name,
                             extenttype="Polygon")

###############################################################################
# Create offset coordinate system
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create an offset coordinate system to match ODB++ with the
# Sherlock STEP file.

bb = ipk.modeler.user_defined_components[component_name+"1"].bounding_box
stackup_thickness = bb[-1] - bb[2]
ipk.modeler.create_coordinate_system(
    origin=[0, 0, stackup_thickness / 2], mode="view", view="XY"
)

###############################################################################
# Import CAD file
# ~~~~~~~~~~~~~~~
# Import a CAD file and delete the CAD "pcb" object as the ECAD is already in the design.

ipk.modeler.import_3d_cad(file_path, refresh_all_ids=False)
ipk.modeler.delete_objects_containing("pcb", False)

###############################################################################
# Modify air region
# ~~~~~~~~~~~~~
# Modify air region dimensions.

ipk.mesh.global_mesh_region.global_region.padding_values = [20, 20, 20, 20, 300, 300]

###############################################################################
# Assign materials
# ~~~~~~~~~~~~~~~~
# Assign materials from Sherlock file.

ipk.assignmaterial_from_sherlock_files(
    component_file=component_list, material_file=material_list
)

###############################################################################
# Delete objects with no material assignments
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Delete objects with no materials assignments.

no_material_objs = ipk.modeler.get_objects_by_material("")
ipk.modeler.delete(no_material_objs)
ipk.save_project()

###############################################################################
# Assign power to component blocks
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Assign power to component blocks.

all_objects = ipk.modeler.object_names

###############################################################################
# Assign power blocks
# ~~~~~~~~~~~~~~~~~~~
# Assign power blocks from the Sherlock file.

total_power = ipk.assign_block_from_sherlock_file(csv_name=component_list)

###############################################################################
# Assign openings
# ~~~~~~~~~~~~~~~~~~~
# Assign opening boundary condition to all the faces of the region.
ipk.assign_openings(ipk.modeler.get_object_faces("Region"))

###############################################################################
# Plot model
# ~~~~~~~~~~
# Plot the model again now that materials are assigned.

ipk.plot(
    show=False,
    output_file=os.path.join(project_folder, "Sherlock_Example.jpg"),
    plot_air_objects=False,
    plot_as_separate_objects=False
)

###############################################################################
# Set up mesh settings
# ~~~~~~~~~~~~~~~~~
# Mesh settings that is tailored for PCB

ipk.globalMeshSettings(3, gap_min_elements='1', noOgrids=True, MLM_en=True,
                            MLM_Type='2D', edge_min_elements='2', object='Region')

###############################################################################
# Numerical settings
# ~~~~~~~~~~~~~~~~~

setup1 = ipk.create_setup()
setup1.props["Solution Initialization - Y Velocity"] = "1m_per_sec"
setup1.props["Radiation Model"] = "Discrete Ordinates Model"
setup1.props["Include Gravity"] = True
setup1.props["Secondary Gradient"] = True
setup1.props["Convergence Criteria - Max Iterations"] = 100

###############################################################################
# Check for intersections
# ~~~~~~~~~~~~~~~~~~~~~~~
# Check for intersections using validation and fix them by
# assigning priorities.

ipk.assign_priority_on_intersections()

###############################################################################
# Compute power budget
# ~~~~~~~~~~~~~~~~~~~~

power_budget, total = ipk.post.power_budget("W")
print(total)

###############################################################################
# Save project and release AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Save the project and release AEDT.

ipk.save_project()

end = time.time() - start
print("Elapsed time: {}".format(datetime.timedelta(seconds=end)))
print("Project Saved in {} ".format(ipk.project_file))
ipk.release_desktop()
