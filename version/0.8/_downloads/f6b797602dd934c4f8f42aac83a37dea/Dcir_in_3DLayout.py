"""
HFSS 3D Layout: SIwave DCIR analysis in HFSS 3D Layout
------------------------------------------------------
This example shows how you can use configure HFSS 3D Layout for SIwave DCIR
analysis.
"""

import os
import tempfile
import pyaedt

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

###############################################################################
# Configure EDB for DCIR analysis
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copy example into temporary folder
temp_dir = tempfile.gettempdir()
dst_dir = os.path.join(temp_dir, pyaedt.generate_unique_name("pyaedt_dcir"))
os.mkdir(dst_dir)
local_path = pyaedt.downloads.download_aedb(dst_dir)

#####################################################################################
# Load example board into EDB

appedb = pyaedt.Edb(local_path, edbversion=aedt_version)

#####################################################################################
# Create pin group on VRM positive pins

gnd_name = "GND"
appedb.siwave.create_pin_group_on_net(
    reference_designator="U3A1",
    net_name="BST_V3P3_S5",
    group_name="U3A1-BST_V3P3_S5")

#####################################################################################
# Create pin group on VRM negative pins

appedb.siwave.create_pin_group_on_net(
    reference_designator="U3A1",
    net_name="GND",
    group_name="U3A1-GND")

#####################################################################################
# Create voltage source between VRM positive and negative pin groups
appedb.siwave.create_voltage_source_on_pin_group(
    pos_pin_group_name="U3A1-BST_V3P3_S5",
    neg_pin_group_name="U3A1-GND",
    magnitude=3.3,
    name="U3A1-BST_V3P3_S5"
)

#####################################################################################
# Create pin group on sink component positive pins

appedb.siwave.create_pin_group_on_net(
    reference_designator="U2A5",
    net_name="V3P3_S5",
    group_name="U2A5-V3P3_S5")

#####################################################################################
# Create pin group on sink component negative pins

appedb.siwave.create_pin_group_on_net(
    reference_designator="U2A5",
    net_name="GND",
    group_name="U2A5-GND")

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create place current source between sink component positive and negative pin groups
appedb.siwave.create_current_source_on_pin_group(
    pos_pin_group_name="U2A5-V3P3_S5",
    neg_pin_group_name="U2A5-GND",
    magnitude=1,
    name="U2A5-V3P3_S5"
)

###############################################################################
# Add SIwave DCIR analysis

appedb.siwave.add_siwave_dc_analysis(name="my_setup")

###############################################################################
# Save and close EDB
# ~~~~~~~~~~~~~~~~~~
# Save and close EDB.

appedb.save_edb()
appedb.close_edb()

###############################################################################
# Analysis DCIR in AEDT
# ~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT and import the configured EDB and analysis DCIR
desktop = pyaedt.Desktop(aedt_version, non_graphical=False, new_desktop_session=True)
hfss3dl = pyaedt.Hfss3dLayout(local_path)
hfss3dl.analyze()
hfss3dl.save_project()

###############################################################################
# Get element data
# ~~~~~~~~~~~~~~~~~~~
# Get current source

current_source = hfss3dl.get_dcir_element_data_current_source(setup="my_setup")
print(current_source)

# ~~~~~~~~~~~~~~~~~~~
# Get via information

via = hfss3dl.get_dcir_element_data_via(setup="my_setup")
print(via)


###############################################################################
# Get voltage
# ~~~~~~~~~~~
# Get voltage from dcir solution data
voltage = hfss3dl.get_dcir_solution_data(setup="my_setup", show="Sources", category="Voltage")
print({expression: voltage.data_magnitude(expression) for expression in voltage.expressions})

###############################################################################
# Close AEDT
# ~~~~~~~~~~
desktop.release_desktop()
