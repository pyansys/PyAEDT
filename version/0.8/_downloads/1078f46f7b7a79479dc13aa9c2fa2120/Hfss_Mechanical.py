"""
Multiphysics: HFSS-Mechanical multiphysics analysis
---------------------------------------------------
This example shows how you can use PyAEDT to create a multiphysics workflow that
includes Circuit, HFSS, and Mechanical.
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
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

###############################################################################
# Download and open project
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Download and open the project. Save it to the temporary folder.

project_temp_name = pyaedt.downloads.download_via_wizard(pyaedt.generate_unique_folder_name())

###############################################################################
# Start HFSS
# ~~~~~~~~~~
# Start HFSS and initialize the PyAEDT object.

hfss = pyaedt.Hfss(projectname=project_temp_name, specified_version=aedt_version, non_graphical=non_graphical,
                   new_desktop_session=True)
pin_names = hfss.excitations
hfss.change_material_override(True)

###############################################################################
# Start Circuit
# ~~~~~~~~~~~~~
# Start Circuit and add the HFSS dynamic link component to it.

circuit = pyaedt.Circuit()
hfss_comp = circuit.modeler.schematic.add_subcircuit_dynamic_link(hfss)

###############################################################################
# Set up dynamic link options
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Set up dynamic link options. The argument for the ``set_sim_option_on_hfss_subcircuit``
# method can be the component name, component ID, or component object.

circuit.modeler.schematic.refresh_dynamic_link(hfss_comp.composed_name)
circuit.modeler.schematic.set_sim_option_on_hfss_subcircuit(hfss_comp)
hfss_setup_name = hfss.setups[0].name + " : " + hfss.setups[0].sweeps[0].name
circuit.modeler.schematic.set_sim_solution_on_hfss_subcircuit(hfss_comp.composed_name, hfss_setup_name)

###############################################################################
# Create ports and excitations
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create ports and excitations. Find component pin locations and create interface
# ports on them. Define the voltage source on the input port.

circuit.modeler.schematic.create_interface_port(
    name="Excitation_1", location=[hfss_comp.pins[0].location[0], hfss_comp.pins[0].location[1]]
)
circuit.modeler.schematic.create_interface_port(
    name="Excitation_2", location=[hfss_comp.pins[1].location[0], hfss_comp.pins[1].location[1]]
)
circuit.modeler.schematic.create_interface_port(
    name="Port_1", location=[hfss_comp.pins[2].location[0], hfss_comp.pins[2].location[1]]
)
circuit.modeler.schematic.create_interface_port(
    name="Port_2", location=[hfss_comp.pins[3].location[0], hfss_comp.pins[3].location[1]]
)

voltage = 1
phase = 0
ports_list = ["Excitation_1", "Excitation_2"]
source = circuit.assign_voltage_sinusoidal_excitation_to_ports(ports_list)
source.ac_magnitude = voltage
source.phase = phase

###############################################################################
# Create setup
# ~~~~~~~~~~~~
# Create a setup.

setup_name = "MySetup"
LNA_setup = circuit.create_setup(name=setup_name)
bw_start = 4.3
bw_stop = 4.4
n_points = 1001
unit = "GHz"
sweep_list = ["LINC", str(bw_start) + unit, str(bw_stop) + unit, str(n_points)]
LNA_setup.props["SweepDefinition"]["Data"] = " ".join(sweep_list)

###############################################################################
# Solve and push excitations
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Solve the circuit and push excitations to the HFSS model to calculate the
# correct value of losses.

circuit.analyze()
circuit.push_excitations(instance="S1", setup=setup_name)


###############################################################################
# Start Mechanical
# ~~~~~~~~~~~~~~~~
# Start Mechanical and copy bodies from the HFSS project.

mech = pyaedt.Mechanical()
mech.copy_solid_bodies_from(hfss)
mech.change_material_override(True)

###############################################################################
# Get losses from HFSS and assign convection to Mechanical
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get losses from HFSS and assign the convection to Mechanical.

mech.assign_em_losses(design=hfss.design_name, setup=hfss.setups[0].name, sweep="LastAdaptive",
                      map_frequency=hfss.setups[0].props["Frequency"], surface_objects=hfss.get_all_conductors_names())
diels = ["1_pd", "2_pd", "3_pd", "4_pd", "5_pd"]
for el in diels:
    mech.assign_uniform_convection(assignment=[mech.modeler[el].top_face_y, mech.modeler[el].bottom_face_y],
                                   convection_value=3)

###############################################################################
# Plot model
# ~~~~~~~~~~
# Plot the model.

mech.plot(show=False, export_path=os.path.join(mech.working_directory, "Mech.jpg"), plot_air_objects=False)

###############################################################################
# Solve and plot thermal results
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Solve and plot the thermal results.

mech.create_setup()
mech.save_project()
mech.analyze()
surfaces = []
for name in mech.get_all_conductors_names():
    surfaces.extend(mech.modeler.get_object_faces(name))
mech.post.create_fieldplot_surface(assignment=surfaces, quantity="Temperature")

###############################################################################
# Release AEDT
# ~~~~~~~~~~~~
# Release AEDT.

mech.release_desktop(True, True)
