"""
Circuit: schematic subcircuit management
----------------------------------------
This example shows how you can use PyAEDT to add a subcircuit to a circuit design.
It pushes down the child subcircuit and pops up to the parent design.
"""
##########################################################
# Perform required import
# ~~~~~~~~~~~~~~~~~~~~~~~
# Perform the required import.

import os
import pyaedt

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

##########################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

###############################################################################
# Launch AEDT with Circuit
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT 2023 R2 in graphical mode with Circuit.

circuit = pyaedt.Circuit(projectname=pyaedt.generate_unique_project_name(),
                         specified_version=aedt_version,
                         non_graphical=non_graphical,
                         new_desktop_session=True
                         )
circuit.modeler.schematic_units = "mil"

###############################################################################
# Add subcircuit
# ~~~~~~~~~~~~~~
# Add a new subcircuit to the previously created circuit design, creating a
# child circuit. Push this child circuit down into the child subcircuit.

subcircuit = circuit.modeler.schematic.create_subcircuit(location=[0.0, 0.0])
subcircuit_name = subcircuit.composed_name
circuit.push_down(subcircuit)

###############################################################################
# Parametrize subcircuit
# ~~~~~~~~~~~~~~~~~~~~~~
# Parametrize the subcircuit and add a resistor, inductor, and a capacitor with
# the parameter values in the following code example. Connect them in series
# and then use the ``pop_up`` # method to get back to the parent design.

circuit.variable_manager.set_variable(variable_name="R_val", expression="35ohm")
circuit.variable_manager.set_variable(variable_name="L_val", expression="1e-7H")
circuit.variable_manager.set_variable(variable_name="C_val", expression="5e-10F")
p1 = circuit.modeler.schematic.create_interface_port(name="In")
r1 = circuit.modeler.schematic.create_resistor(value="R_val")
l1 = circuit.modeler.schematic.create_inductor(value="L_val")
c1 = circuit.modeler.schematic.create_capacitor(value="C_val")
p2 = circuit.modeler.schematic.create_interface_port(name="Out")
circuit.modeler.schematic.connect_components_in_series(assignment=[p1, r1, l1, c1, p2], use_wire=True)
circuit.pop_up()


###############################################################################
# Release AEDT
# ~~~~~~~~~~~~
# Release AEDT.

circuit.release_desktop(True, True)
