"""
EMIT: HFSS to EMIT coupling
---------------------------
This example shows how you can use PyAEDT to open an AEDT project with
an HFSS design, create an EMIT design in the project, and link the HFSS design
as a coupling link in the EMIT design.
"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.
#
# sphinx_gallery_thumbnail_path = "Resources/emit_hfss.png"

import os

# Import required modules
import pyaedt
from pyaedt.generic.filesystem import Scratch
from pyaedt.emit_core.emit_constants import TxRxMode, ResultType

###############################################################################
## Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.
# The Boolean parameter ``new_thread`` defines whether to create a new instance
# of AEDT or try to connect to an existing instance of it.
# 
# The following code uses AEDT 2023 R2.

non_graphical = False
NewThread = True
desktop_version = "2023.2"
scratch_path = pyaedt.generate_unique_folder_name()

###############################################################################
# Launch AEDT with EMIT
# ~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT with EMIT. The ``Desktop`` class initializes AEDT and starts it
# on the specified version and in the specified graphical mode.

d = pyaedt.launch_desktop(desktop_version, non_graphical, NewThread)

temp_folder = os.path.join(scratch_path, ("EmitHFSSExample"))
if not os.path.exists(temp_folder):
    os.mkdir(temp_folder)

example_name = "Cell Phone RFI Desense"
example_aedt = example_name + ".aedt"
example_results = example_name + ".aedtresults"
example_lock = example_aedt + ".lock"
example_pdf_file = example_name + " Example.pdf"

example_dir = os.path.join(d.install_path, "Examples\\EMIT")
example_project = os.path.join(example_dir, example_aedt)
example_results_folder = os.path.join(example_dir, example_results)
example_pdf = os.path.join(example_dir, example_pdf_file)

########################################################################################################
# If the ``Cell Phone RFT Defense`` example is not
# in the installation directory, exit from this example.

if not os.path.exists(example_project):
    msg = """
        Cell phone RFT Desense example file is not in the
         Examples/EMIT directory under the EDT installation. You cannot run this example.
        """
    print(msg)
    d.release_desktop(True, True)
    exit()

my_project = os.path.join(temp_folder, example_aedt)
my_results_folder = os.path.join(temp_folder, example_results)
my_project_lock = os.path.join(temp_folder, example_lock)
my_project_pdf = os.path.join(temp_folder, example_pdf_file)

if os.path.exists(my_project):
    os.remove(my_project)

if os.path.exists(my_project_lock):
    os.remove(my_project_lock)

with Scratch(scratch_path) as local_scratch:
    local_scratch.copyfile(example_project, my_project)
    local_scratch.copyfolder(example_results_folder, my_results_folder)
    if os.path.exists(example_pdf):
        local_scratch.copyfile(example_pdf, my_project_pdf)

aedtapp = pyaedt.Emit(my_project)

###############################################################################
# Create and connect EMIT components
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create two radios with antennas connected to each one.

rad1, ant1 = aedtapp.modeler.components.create_radio_antenna("Bluetooth Low Energy (LE)")
rad2, ant2 = aedtapp.modeler.components.create_radio_antenna("Bluetooth Low Energy (LE)")

###############################################################################
# Define coupling among RF systems
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Define coupling among the RF systems.

for link in aedtapp.couplings.linkable_design_names:
    aedtapp.couplings.add_link(link)

for link in aedtapp.couplings.coupling_names:
    aedtapp.couplings.update_link(link)

###############################################################################
# Run EMIT simulation
# ~~~~~~~~~~~~~~~~~~~
# Run the EMIT simulation. This portion of the EMIT API is not yet implemented.
#
# This part of the example requires Ansys AEDT 2023 R2. 

if desktop_version > "2023.1":
    rev = aedtapp.results.analyze()
    rx_bands = rev.get_band_names(rad1.name, TxRxMode.RX) 
    tx_bands = rev.get_band_names(rad2.name, TxRxMode.TX) 
    domain = aedtapp.results.interaction_domain()
    domain.set_receiver(rad1.name, rx_bands[0], -1)
    domain.set_interferer(rad2.name,tx_bands[0])
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
