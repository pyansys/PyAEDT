"""
EDB: Edit Control File and import gds
-------------------------------------
This example shows how you can use PyAEDT to import a gds from an IC file.
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports, which includes importing a section.

import os
import tempfile
import pyaedt
import shutil
from pyaedt.edb_core.edb_data.control_file import ControlFile

###############################################################################
# Download file
# ~~~~~~~~~~~~~
# Download the AEDB file and copy it in the temporary folder.
temppath = tempfile.gettempdir()
local_path = pyaedt.downloads.download_file('gds')
c_file_in = os.path.join(
    local_path, "sky130_fictitious_dtc_example_control_no_map.xml"
)
c_map = os.path.join(local_path, "dummy_layermap.map")
gds_in = os.path.join(local_path, "sky130_fictitious_dtc_example.gds")
gds_out = os.path.join(temppath, "example.gds")
shutil.copy2(gds_in,gds_out )
###############################################################################
# Control file
# ~~~~~~~~~~~~
# A Control file is an xml file which purpose if to provide additional
# information during import phase. It can include, materials, stackup, setup, boundaries and settings.
# In this example we will import an exising xml, integrate it with a layer mapping file of gds
# and then adding setup and boundaries.

c = ControlFile(c_file_in, layer_map=c_map)


###############################################################################
# Simulation setup
# ~~~~~~~~~~~~~~~~
# Here we setup simulation with HFSS and add a frequency sweep.
setup = c.setups.add_setup("Setup1", "1GHz")
setup.add_sweep("Sweep1", "0.01GHz", "5GHz", "0.1GHz")

###############################################################################
# Additional stackup settings
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# After import user can change stackup settings and add/remove layers or materials.
c.stackup.units = "um"
c.stackup.dielectrics_base_elevation = -100
c.stackup.metal_layer_snapping_tolerance = "10nm"
for via in c.stackup.vias:
    via.create_via_group = True
    via.snap_via_group = True


###############################################################################
# Boundaries settings
# ~~~~~~~~~~~~~~~~~~~
# Boundaries can include ports, components and boundary extent.

c.boundaries.units = "um"
c.boundaries.add_port("P1", x1=223.7, y1=222.6, layer1="Metal6", x2=223.7, y2=100, layer2="Metal6")
c.boundaries.add_extent()
comp = c.components.add_component("B1", "BGA", "IC", "Flip chip", "Cylinder")
comp.solder_diameter = "65um"
comp.add_pin("1", "81.28", "84.6", "met2")
comp.add_pin("2", "211.28", "84.6", "met2")
comp.add_pin("3", "211.28", "214.6", "met2")
comp.add_pin("4", "81.28", "214.6", "met2")
c.import_options.import_dummy_nets = True

###############################################################################
# Write xml
# ~~~~~~~~~
# After all settings are ready we can write xml.

c.write_xml(os.path.join(temppath, "output.xml"))

###############################################################################
# Open Edb
# ~~~~~~~~~
# Import the gds and open the edb.

from pyaedt import Edb

edb = Edb(gds_out, edbversion="2023.2", technology_file=os.path.join(temppath, "output.xml"))

###############################################################################
# Plot Stackup
# ~~~~~~~~~~~~
# Stackup plot.
edb.stackup.plot(first_layer="met1")

###############################################################################
# Close Edb
# ~~~~~~~~~
# Close the project.

edb.close_edb()