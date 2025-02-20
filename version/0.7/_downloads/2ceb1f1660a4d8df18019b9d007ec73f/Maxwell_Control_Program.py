"""
Enabling Control Program in a Maxwell 2D Project
------------------------------------------------
This example shows how you can use PyAEDT to enable control program in a Maxwell 2D project.
It shows how to create the geometry, load material properties from an Excel file and
set up the mesh settings. Moreover, it focuses on post-processing operations, in particular how to
plot field line traces, relevant for an electrostatic analysis.

"""
#################################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

from pyaedt import downloads
from pyaedt import generate_unique_folder_name
from pyaedt import Maxwell2d

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

#################################################################################
# Download .aedt file example
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Set local temporary folder to export the .aedt file to.
temp_folder = generate_unique_folder_name()
aedt_file = downloads.download_file("maxwell_ctrl_prg", "ControlProgramDemo.aedt", temp_folder)
ctrl_prg_file = downloads.download_file("maxwell_ctrl_prg", "timestep_only.py", temp_folder)

##################################################################################
# Launch Maxwell 2D
# ~~~~~~~~~~~~~~~~~
# Launch Maxwell 2D.

m2d = Maxwell2d(projectname=aedt_file,
                specified_version="2023.2",
                new_desktop_session=True,
                non_graphical=non_graphical)

##################################################################################
# Set active design
# ~~~~~~~~~~~~~~~~~
# Set active design.

m2d.set_active_design("1 time step control")

##################################################################################
# Get design setup
# ~~~~~~~~~~~~~~~~
# Get design setup to enable the control program to.

setup = m2d.setups[0]

##################################################################################
# Enable control program
# ~~~~~~~~~~~~~~~~~~~~~~
# Enable control program by giving the path to the file.

setup.enable_control_program(control_program_path=ctrl_prg_file)

##################################################################################
# Analyze setup
# ~~~~~~~~~~~~~
# Analyze setup.

setup.analyze()


##################################################################################
# Plot results
# ~~~~~~~~~~~~
# Plot Solved Results.

sols = m2d.post.get_solution_data("FluxLinkage(Winding1)",variations={"Time":["All"]},  primary_sweep_variable="Time")
sols.plot()

###################################################################################
# Save project and close AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Save the project and close AEDT.

m2d.save_project()
m2d.release_desktop()
