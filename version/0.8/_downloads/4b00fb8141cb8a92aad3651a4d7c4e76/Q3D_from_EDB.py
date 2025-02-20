"""
Q3D Extractor: PCB analysis
---------------------------
This example shows how you can use PyAEDT to create a design in
Q3D Extractor and run a simulation starting from an EDB Project.
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import pyaedt

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

###############################################################################
# Setup project files and path
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Download of needed project file and setup of temporary project directory.

project_dir = pyaedt.generate_unique_folder_name()
aedb_project = pyaedt.downloads.download_file('edb/ANSYS-HSD_V1.aedb',destination=project_dir)

project_name = pyaedt.generate_unique_name("HSD")
output_edb = os.path.join(project_dir, project_name + '.aedb')
output_q3d = os.path.join(project_dir, project_name + '_q3d.aedt')

###############################################################################
# Open EDB
# ~~~~~~~~
# Open the edb project and created a cutout on the selected nets
# before exporting to Q3D.

edb = pyaedt.Edb(aedb_project, edbversion=aedt_version)
edb.cutout(["CLOCK_I2C_SCL", "CLOCK_I2C_SDA"], ["GND"], output_aedb_path=output_edb,
                              use_pyaedt_extent_computing=True, )

###############################################################################
# Identify pins position
# ~~~~~~~~~~~~~~~~~~~~~~
# Identify [x,y] pin locations on the components to define where to assign sources
# and sinks for Q3D and append Z elevation.

pin_u13_scl = [i for i in edb.components["U13"].pins.values() if i.net_name == "CLOCK_I2C_SCL"]
pin_u1_scl = [i for i in edb.components["U1"].pins.values() if i.net_name == "CLOCK_I2C_SCL"]
pin_u13_sda = [i for i in edb.components["U13"].pins.values() if i.net_name == "CLOCK_I2C_SDA"]
pin_u1_sda = [i for i in edb.components["U1"].pins.values() if i.net_name == "CLOCK_I2C_SDA"]

###############################################################################
# Append Z Positions
# ~~~~~~~~~~~~~~~~~~
# Note: The factor 100 converts from "meters" to "mm"

location_u13_scl = [i * 1000 for i in pin_u13_scl[0].position]
location_u13_scl.append(edb.components["U13"].upper_elevation * 1000)

location_u1_scl = [i * 1000 for i in pin_u1_scl[0].position]
location_u1_scl.append(edb.components["U1"].upper_elevation * 1000)

location_u13_sda = [i * 1000 for i in pin_u13_sda[0].position]
location_u13_sda.append(edb.components["U13"].upper_elevation * 1000)

location_u1_sda = [i * 1000 for i in pin_u1_sda[0].position]
location_u1_sda.append(edb.components["U1"].upper_elevation * 1000)

###############################################################################
# Save and close Edb
# ~~~~~~~~~~~~~~~~~~
# Save, close Edb and open it in Hfss 3D Layout to generate the 3D model.

edb.save_edb()
edb.close_edb()

h3d = pyaedt.Hfss3dLayout(output_edb, specified_version=aedt_version, non_graphical=True, new_desktop_session=True)

###############################################################################
# Export to Q3D
# ~~~~~~~~~~~~~
# Create a dummy setup and export the layout in Q3D.
# keep_net_name will reassign Q3D nets names from Hfss 3D Layout.

setup = h3d.create_setup()
setup.export_to_q3d(output_q3d, keep_net_name=True)
h3d.close_project()

###############################################################################
# Open Q3D
# ~~~~~~~~
# Launch the newly created q3d project and plot it.

q3d = pyaedt.Q3d(output_q3d)
q3d.plot(show=False, objects=["CLOCK_I2C_SCL", "CLOCK_I2C_SDA"],
         export_path=os.path.join(q3d.working_directory, "Q3D.jpg"), plot_air_objects=False)

###############################################################################
# Assign Source and Sink
# ~~~~~~~~~~~~~~~~~~~~~~
# Use previously calculated position to identify faces and
# assign sources and sinks on nets.

f1 = q3d.modeler.get_faceid_from_position(location_u13_scl, assignment="CLOCK_I2C_SCL")
q3d.source(f1, net_name="CLOCK_I2C_SCL")
f1 = q3d.modeler.get_faceid_from_position(location_u13_sda, assignment="CLOCK_I2C_SDA")
q3d.source(f1, net_name="CLOCK_I2C_SDA")
f1 = q3d.modeler.get_faceid_from_position(location_u1_scl, assignment="CLOCK_I2C_SCL")
q3d.sink(f1, net_name="CLOCK_I2C_SCL")
f1 = q3d.modeler.get_faceid_from_position(location_u1_sda, assignment="CLOCK_I2C_SDA")
q3d.sink(f1, net_name="CLOCK_I2C_SDA")

###############################################################################
# Create Setup
# ~~~~~~~~~~~~
# Create a setup and a frequency sweep from DC to 2GHz.
# Analyze project.

setup = q3d.create_setup()
setup.dc_enabled = True
setup.capacitance_enabled = False
sweep = setup.add_sweep()
sweep.add_subrange("LinearStep", 0, end=2, count=0.05, unit="GHz", save_single_fields=False, clear=True)
setup.analyze()

###############################################################################
# ACL Report
# ~~~~~~~~~~
# Compute ACL solutions and plot them.

traces_acl = q3d.post.available_report_quantities(quantities_category="ACL Matrix")
solution = q3d.post.get_solution_data(traces_acl)
solution.plot()

###############################################################################
# ACR Report
# ~~~~~~~~~~
# Compute ACR solutions and plot them.

traces_acr = q3d.post.available_report_quantities(quantities_category="ACR Matrix")
solution2 = q3d.post.get_solution_data(traces_acr)
solution2.plot()

###############################################################################
# Close AEDT
# ~~~~~~~~~~
# After the simulation completes, you can close AEDT or release it using the
# ``release_desktop`` method. All methods provide for saving projects before closing.

q3d.release_desktop()
