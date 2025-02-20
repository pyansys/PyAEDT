"""
Circuit: netlist to schematic import
------------------------------------
This example shows how you can import netlist data into a circuit design.
HSPICE files are fully supported. Mentor files are partially supported.
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports and set paths.

import os

import pyaedt

netlist = pyaedt.downloads.download_netlist()

project_name = pyaedt.generate_unique_project_name()
print(project_name)

###############################################################################
# Launch AEDT
# ~~~~~~~~~~~
# Launch AEDT 2023 R2 in graphical mode. This example uses SI units.
desktopVersion = "2023.2"

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.
# The Boolean parameter ``NewThread`` defines whether to create a new instance
# of AEDT or try to connect to an existing instance of it.

non_graphical = False
NewThread = True

###############################################################################
# Launch AEDT with Circuit
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT with Circuit. The :class:`pyaedt.Desktop` class initializes AEDT
# and starts it on the specified version in the specified graphical mode.

desktop = pyaedt.launch_desktop(desktopVersion, non_graphical, NewThread)
aedtapp = pyaedt.Circuit(projectname=project_name)

###############################################################################
# Define variable
# ~~~~~~~~~~~~~~~
# Define a design variable by using a ``$`` prefix.

aedtapp["Voltage"] = "5"

###############################################################################
# Create schematic from netlist file
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a schematic from a netlist file. The ``create_schematic_from_netlist``
# method reads the netlist file and parses it. All components are parsed
# but only these categories are mapped: R, L, C, Q, U, J, V, and I.

aedtapp.create_schematic_from_netlist(netlist)

###############################################################################
# Close project and release AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# After adding any other desired functionalities, close the project and release
# AEDT.

desktop.release_desktop()
