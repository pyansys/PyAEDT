"""
EMIT: antenna
---------------------
This example shows how you can use PyAEDT to create a project in EMIT for
the simulation of an antenna.
"""
###############################################################################
# Perform required inputs
# ~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.
#
# sphinx_gallery_thumbnail_path = "Resources/emit_simple_cosite.png"

import os
import pyaedt
from pyaedt.emit_core.emit_constants import TxRxMode, ResultType

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
# The ``NewThread`` Boolean variable defines whether to create a new instance
# of AEDT or try to connect to existing instance of it if one is available.

non_graphical = False
NewThread = True

###############################################################################
# Launch AEDT with EMIT
# ~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT with EMIT. The ``Desktop`` class initializes AEDT and starts it
# on the specified version and in the specified graphical mode.

d = pyaedt.launch_desktop(aedt_version, non_graphical, NewThread)
aedtapp = pyaedt.Emit(pyaedt.generate_unique_project_name())


###############################################################################
# Create and connect EMIT components
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create three radios and connect an antenna to each one.

rad1 = aedtapp.modeler.components.create_component("New Radio")
ant1 = aedtapp.modeler.components.create_component("Antenna")
if rad1 and ant1:
    ant1.move_and_connect_to(rad1)

# Convenience method to create a radio and antenna connected together
rad2, ant2 = aedtapp.modeler.components.create_radio_antenna("GPS Receiver")
rad3, ant3 = aedtapp.modeler.components.create_radio_antenna("Bluetooth Low Energy (LE)", "Bluetooth")

###############################################################################
# Define coupling among RF systems
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Define the coupling among the RF systems. This portion of the EMIT API is not
# yet implemented.


###############################################################################
# Run EMIT simulation
# ~~~~~~~~~~~~~~~~~~~
# Run the EMIT simulation. 
#
# This part of the example requires Ansys AEDT 2023 R2. 

if aedt_version > "2023.1" and os.getenv("PYAEDT_DOC_GENERATION", "False") != "1":
    rev = aedtapp.results.analyze()
    rx_bands = rev.get_band_names(rad2.name, TxRxMode.RX) 
    tx_bands = rev.get_band_names(rad3.name, TxRxMode.TX) 
    domain = aedtapp.results.interaction_domain()
    domain.set_receiver(rad2.name, rx_bands[0], -1)
    domain.set_interferer(rad3.name,tx_bands[0])
    interaction = rev.run(domain)
    worst = interaction.get_worst_instance(ResultType.EMI)
    if worst.has_valid_values():
        emi = worst.get_value(ResultType.EMI)
        print("Worst case interference is: {} dB".format(emi))

###############################################################################
# Save project and close AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# After the simulation completes, you can close AEDT or release it using the
# :func:`pyaedt.Desktop.force_close_desktop` method.
# All methods provide for saving the project before closing.

aedtapp.save_project()
aedtapp.release_desktop(close_projects=True, close_desktop=True)
