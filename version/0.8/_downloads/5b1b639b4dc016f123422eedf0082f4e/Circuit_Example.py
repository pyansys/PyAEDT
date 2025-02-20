"""
Circuit: schematic creation and analysis
----------------------------------------
This example shows how you can use PyAEDT to create a circuit design
and run a Nexxim time-domain simulation.
"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

# sphinx_gallery_thumbnail_path = 'Resources/circuit.png'

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
# The Boolean parameter ``new_thread`` defines whether to create a new instance
# of AEDT or try to connect to an existing instance of it.

non_graphical = False
new_thread = True

###############################################################################
# Launch AEDT and Circuit
# ~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT and Circuit. The :class:`pyaedt.Desktop` class initializes AEDT and
# starts the specified version in the specified mode.

desktop = pyaedt.launch_desktop(aedt_version, non_graphical, new_thread)
aedt_app = pyaedt.Circuit(projectname=pyaedt.generate_unique_project_name())
aedt_app.modeler.schematic.schematic_units = "mil"
###############################################################################
# Create circuit setup
# ~~~~~~~~~~~~~~~~~~~~
# Create and customize an LNA (linear network analysis) setup.

setup1 = aedt_app.create_setup("MyLNA")
setup1.props["SweepDefinition"]["Data"] = "LINC 0GHz 4GHz 10001"

###############################################################################
# Create components
# ~~~~~~~~~~~~~~~~~
# Create components, such as an inductor, resistor, and capacitor.

inductor = aedt_app.modeler.schematic.create_inductor(name="L1", value=1e-9, location=[0, 0])
resistor = aedt_app.modeler.schematic.create_resistor(name="R1", value=50, location=[500, 0])
capacitor = aedt_app.modeler.schematic.create_capacitor(name="C1", value=1e-12, location=[1000, 0])

###############################################################################
# Get all pins
# ~~~~~~~~~~~~
# Get all pins of a specified component.

pins_resistor = resistor.pins

###############################################################################
# Create port and ground
# ~~~~~~~~~~~~~~~~~~~~~~
# Create a port and a ground, which are needed for the circuit analysis.

port = aedt_app.modeler.components.create_interface_port(name="myport", location=[-200, 0] )
gnd = aedt_app.modeler.components.create_gnd(location=[1200, -100])

###############################################################################
# Connect components
# ~~~~~~~~~~~~~~~~~~
# Connect components with wires.

port.pins[0].connect_to_component(assignment=inductor.pins[0], use_wire=True)
inductor.pins[1].connect_to_component(assignment=resistor.pins[1], use_wire=True)
resistor.pins[0].connect_to_component(assignment=capacitor.pins[0], use_wire=True)
capacitor.pins[1].connect_to_component(assignment=gnd.pins[0], use_wire=True)

###############################################################################
# Create transient setup
# ~~~~~~~~~~~~~~~~~~~~~~
# Create a transient setup.

setup2 = aedt_app.create_setup(name="MyTransient", setup_type=aedt_app.SETUPS.NexximTransient)
setup2.props["TransientData"] = ["0.01ns", "200ns"]
setup3 = aedt_app.create_setup(name="MyDC", setup_type=aedt_app.SETUPS.NexximDC)

###############################################################################
# Solve transient setup
# ~~~~~~~~~~~~~~~~~~~~~
# Solve the transient setup.

aedt_app.analyze_setup("MyLNA")
aedt_app.export_fullwave_spice()

###############################################################################
# Create report
# ~~~~~~~~~~~~~
# Create a report that plots solution data.

solutions = aedt_app.post.get_solution_data(expressions=aedt_app.get_traces_for_plot(category="S"))
solutions.enable_pandas_output = True
real, imag = solutions.full_matrix_real_imag
print(real)

###############################################################################
# Plot data
# ~~~~~~~~~
# Create a plot based on solution data.

fig = solutions.plot()

###############################################################################
# Close AEDT
# ~~~~~~~~~~
# After the simulation completes, you can close AEDT or release it using the
# :func:`pyaedt.Desktop.force_close_desktop` method.
# All methods provide for saving the project before closing.

desktop.release_desktop()
