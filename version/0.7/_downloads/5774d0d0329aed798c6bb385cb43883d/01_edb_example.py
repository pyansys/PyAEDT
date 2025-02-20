"""
EDB: Siwave analysis from EDB setup
-----------------------------------
This example shows how you can use EDB to interact with a layout.
"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import time
import pyaedt

temp_folder = pyaedt.generate_unique_folder_name()
targetfile = pyaedt.downloads.download_file('edb/ANSYS-HSD_V1.aedb', destination=temp_folder)

siwave_file = os.path.join(os.path.dirname(targetfile), "ANSYS-HSD_V1.siw")
print(targetfile)
aedt_file = targetfile[:-4] + "aedt"


###############################################################################
# Launch EDB
# ~~~~~~~~~~
# Launch the :class:`pyaedt.Edb` class, using EDB 2023 R2 and SI units.
edb_version = "2023.2"
if os.path.exists(aedt_file):
    os.remove(aedt_file)
edb = pyaedt.Edb(edbpath=targetfile, edbversion=edb_version)

###############################################################################
# Compute nets and components
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Computes nets and components.
# There are queries for nets, stackups, layers, components, and geometries.

print("Nets {}".format(len(edb.nets.netlist)))
start = time.time()
print("Components {}".format(len(edb.components.components.keys())))
print("elapsed time = ", time.time() - start)

###############################################################################
# Get pin position
# ~~~~~~~~~~~~~~~~
# Get the position for a specific pin.
# The next section shows how to get all pins for a specific component and
# the positions of each of them.
# Each pin is a list of ``[X, Y]`` coordinate positions.

pins = edb.components["U2"].pins
for pin in edb.components["U2"].pins.values():
    print(pin.position)

###############################################################################
# Get all nets connected to a component
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get all nets connected to a specific component.

edb.components.get_component_net_connection_info("U2")

###############################################################################
# Compute rats
# ~~~~~~~~~~~~
# Computes rats.

rats = edb.components.get_rats()

###############################################################################
# Get all DC-connected net lists through inductance
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get all DC-connected net lists through inductance.
# The inputs needed are ground net lists. The returned list contains all nets
# connected to a ground through an inductor.

GROUND_NETS = ["GND", "GND_DP"]
dc_connected_net_list = edb.nets.get_dcconnected_net_list(GROUND_NETS)
print(dc_connected_net_list)

###############################################################################
# Get power tree based on a specific net
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get the power tree based on a specific net.

VRM = "U1"
OUTPUT_NET = "AVCC_1V3"
powertree_df, component_list_columns, net_group = edb.nets.get_powertree(OUTPUT_NET, GROUND_NETS)
for el in powertree_df:
    print(el)

###############################################################################
# Delete all RLCs with only one pin
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Delete all RLCs with only one pin. This method provides a useful way of
# removing components not needed in the simulation.

edb.components.delete_single_pin_rlc()

###############################################################################
# Delete components
# ~~~~~~~~~~~~~~~~~
# Delete manually one or more components.

edb.components.delete("C380")

###############################################################################
# Delete nets
# ~~~~~~~~~~~
# Delete manually one or more nets.

edb.nets.delete("PDEN")

###############################################################################
# Get stackup limits
# ~~~~~~~~~~~~~~~~~~
# Get the stackup limits (top and bottom layers and elevations).

print(edb.stackup.limits())



###############################################################################
# Create voltage source and Siwave DCIR analysis
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a voltage source and then set up a DCIR analysis.

edb.siwave.create_voltage_source_on_net("U1", "AVCC_1V3", "U1", "GND", 1.3, 0, "V1")
edb.siwave.create_current_source_on_net("IC2", "NetD3_2", "IC2", "GND", 1.0, 0, "I1")
setup = edb.siwave.add_siwave_dc_analysis("myDCIR_4")
setup.use_dc_custom_settings = True
setup.set_dc_slider = 0
setup.add_source_terminal_to_ground("V1", 1)



###############################################################################
# Save modifications
# ~~~~~~~~~~~~~~~~~~
# Save modifications.

edb.save_edb()
edb.nets.plot(None, "1_Top",plot_components_on_top=True)

siw_file = edb.solve_siwave()

###############################################################################
# Export Siwave Reports
# ~~~~~~~~~~~~~~~~~~~~~
# Export all DC Reports quantities.
outputs = edb.export_siwave_dc_results(siw_file, setup.name, )

###############################################################################
# Close EDB
# ~~~~~~~~~
# Close EDB. After EDB is closed, it can be opened by AEDT.

edb.close_edb()

###############################################################################
# Postprocess in Siwave
# ~~~~~~~~~~~~~~~~~~~~~
# Open Siwave and generate a report. This works on Window only.

# from pyaedt import Siwave
# siwave = Siwave("2023.2")
# siwave.open_project(siwave_file)
# report_file = os.path.join(temp_folder,'Ansys.htm')
#
# siwave.export_siwave_report("myDCIR_4", report_file)
# siwave.close_project()
# siwave.quit_application()
