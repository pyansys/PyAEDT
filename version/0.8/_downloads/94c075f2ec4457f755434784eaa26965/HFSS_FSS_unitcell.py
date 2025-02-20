"""
HFSS: FSS Unitcell Simulation
--------------------
This example shows how you can use PyAEDT to create a FSS unitcell simulations in HFSS and postprocess results.
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import pyaedt

project_name = pyaedt.generate_unique_project_name(project_name="FSS")

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. `
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

###############################################################################
# Launch AEDT
# ~~~~~~~~~~~
# Launch AEDT 2023 R2 in graphical mode.

d = pyaedt.launch_desktop(aedt_version, non_graphical=non_graphical, new_desktop_session=True)

###############################################################################
# Launch HFSS
# ~~~~~~~~~~~
# Launch HFSS 2023 R2 in graphical mode.

hfss = pyaedt.Hfss(projectname=project_name, solution_type="Modal")

###############################################################################
# Define variable
# ~~~~~~~~~~~~~~~
# Define a variable for the 3D-component.

hfss["patch_dim"] = "10mm"

###############################################################################
# Insert 3D component from system library
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Download the 3D component from the example data and insert the 3D Component.

unitcell_3d_component_path = pyaedt.downloads.download_FSS_3dcomponent()
unitcell_path = os.path.join(unitcell_3d_component_path, "FSS_unitcell_23R2.a3dcomp")

comp = hfss.modeler.insert_3d_component(unitcell_path)

###############################################################################
# Assign design parameter to 3D Component parameter
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Assign parameter.

component_name = hfss.modeler.user_defined_component_names
comp.parameters["a"] = "patch_dim"

###############################################################################
# Create air region
# ~~~~~~~~~~~~~~~~~
# Create an open region along +Z direction for unitcell analysis.

bounding_dimensions = hfss.modeler.get_bounding_dimension()

periodicity_x = bounding_dimensions[0]
periodicity_y = bounding_dimensions[1]

region = hfss.modeler.create_air_region(
        z_pos=10 * bounding_dimensions[2],
        is_percentage=False,
    )

[x_min, y_min, z_min, x_max, y_max, z_max] = region.bounding_box

###############################################################################
# Assign Lattice pair boundary
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Assigning lattice pair boundary automatically detected.

hfss.auto_assign_lattice_pairs(assignment=region.name)

###############################################################################
# Assign Floquet port excitation along +Z direction
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Assign Floquet port.

id_z_pos = region.top_face_z
hfss.create_floquet_port(id_z_pos, [0, 0, z_max], [0, y_max, z_max], [x_max, 0, z_max], name='port_z_max',
                         deembed_distance=10 * bounding_dimensions[2])


###############################################################################
# Create setup
# ~~~~~~~~~~~~
# Create a setup with a sweep to run the simulation.

setup = hfss.create_setup("MySetup")
setup.props["Frequency"] = "10GHz"
setup.props["MaximumPasses"] = 10
hfss.create_linear_count_sweep(setup=setup.name, units="GHz", start_frequency=6, stop_frequency=15,
                               num_of_freq_points=51, name="sweep1", save_fields=False, sweep_type="Interpolating",
                               interpolation_tol=6)

###############################################################################
# Create S-parameter report using report objects
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create S-parameter reports using create report.

all_quantities = hfss.post.available_report_quantities()
str_mag = []
str_ang = []

variation = {"Freq": ["All"]}

for i in all_quantities:
    str_mag.append("mag(" + i + ")")
    str_ang.append("ang_deg(" + i + ")")

hfss.post.create_report(expressions=str_mag, variations=variation, plot_name="magnitude_plot")
hfss.post.create_report(expressions=str_ang, variations=variation, plot_name="phase_plot")

###############################################################################
# Save and run simulation
# ~~~~~~~~~~~~~~~~~~~~~~~
# Save and run the simulation. Uncomment the line following line to run the analysis.

# hfss.analyze()

###############################################################################
# Close AEDT
# ~~~~~~~~~~
# After the simulation completes, you can close AEDT or release it using the
# :func:`pyaedt.Desktop.release_desktop` method.
# All methods provide for saving the project before closing.

hfss.release_desktop()
