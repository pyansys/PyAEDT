"""
Twin Builder: RC circuit design anaysis
---------------------------------------
This example shows how you can use PyAEDT to create a Twin Builder design
and run a Twin Builder time-domain simulation.
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import pyaedt

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

###############################################################################
# Select version and set launch options
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Select the Twin Builder version and set the launch options. The following code
# launches Twin Builder 2023 R2 in graphical mode.
#
# You can change the Boolean parameter ``non_graphical`` to ``True`` to launch
# Twin Builder in non-graphical mode. You can also change the Boolean parameter
# ``new_thread`` to ``False`` to launch Twin Builder in an existing AEDT session
# if one is running.

non_graphical = False
new_thread = True

###############################################################################
# Launch Twin Builder
# ~~~~~~~~~~~~~~~~~~~
# Launch Twin Builder using an implicit declaration and add a new design with
# a default setup.

tb = pyaedt.TwinBuilder(projectname=pyaedt.generate_unique_project_name(),
                        specified_version=aedt_version,
                        non_graphical=non_graphical,
                        new_desktop_session=new_thread
                        )
tb.modeler.schematic_units = "mil"

###############################################################################
# Create components for RC circuit
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create components for an RC circuit driven by a pulse voltage source.
# Create components, such as a voltage source, resistor, and capacitor.

source = tb.modeler.schematic.create_voltage_source("E1", "EPULSE", 10, 10, [0, 0])
resistor = tb.modeler.schematic.create_resistor("R1", 10000, [1000, 1000], 90)
capacitor = tb.modeler.schematic.create_capacitor("C1", 1e-6, [2000, 0])

###############################################################################
# Create ground
# ~~~~~~~~~~~~~
# Create a ground, which is needed for an analog analysis.

gnd = tb.modeler.components.create_gnd([0, -1000])

###############################################################################
# Connect components
# ~~~~~~~~~~~~~~~~~~
# Connects components with pins.

source.pins[1].connect_to_component(resistor.pins[0])
resistor.pins[1].connect_to_component(capacitor.pins[0])
capacitor.pins[1].connect_to_component(source.pins[0])
source.pins[0].connect_to_component(gnd.pins[0])

###############################################################################
# Parametrize transient setup
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Parametrize the default transient setup by setting the end time.

tb.set_end_time("300ms")

###############################################################################
# Solve transient setup
# ~~~~~~~~~~~~~~~~~~~~~
# Solve the transient setup.

tb.analyze_setup("TR")


###############################################################################
# Get report data and plot using Matplotlib
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get report data and plot it using Matplotlib. The following code gets and plots
# the values for the voltage on the pulse voltage source and the values for the
# voltage on the capacitor in the RC circuit.

E_Value = "E1.V"
C_Value = "C1.V"

x = tb.post.get_solution_data([E_Value, C_Value], "TR", "Time")
x.plot([E_Value, C_Value], x_label="Time", y_label="Capacitor Voltage vs Input Pulse")

tb.save_project()

###############################################################################
# Close Twin Builder
# ~~~~~~~~~~~~~~~~~~
# After the simulation completes, you can close Twin Builder or release it.
# All methods provide for saving the project before closing.

tb.release_desktop()
