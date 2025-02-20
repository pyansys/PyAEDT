"""
EDB: geometry creation
----------------------
This example shows how you can use EDB to create a layout.
"""
######################################################################
# Final expected project
# ~~~~~~~~~~~~~~~~~~~~~~
#
# .. image:: ../../_static/diff_via.png
#  :width: 600
#  :alt: Differential Vias.
######################################################################

######################################################################
# Import EDB layout object
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Import the EDB layout object and initialize it on version 2023 R2.
######################################################################

import time
import os
import pyaedt

start = time.time()

aedb_path = os.path.join(pyaedt.generate_unique_folder_name(), pyaedt.generate_unique_name("pcb") + ".aedb")
print(aedb_path)
edb = pyaedt.Edb(edbpath=aedb_path, edbversion="2023.2")

####################
# Add stackup layers
# ~~~~~~~~~~~~~~~~~~
# Add stackup layers.
# A stackup can be created layer by layer or imported from a csv file or xml file.
#

edb.stackup.add_layer("GND")
edb.stackup.add_layer("Diel", "GND", layer_type="dielectric", thickness="0.1mm", material="FR4_epoxy")
edb.stackup.add_layer("TOP", "Diel", thickness="0.05mm")

#####################################
# Create signal net and ground planes
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a signal net and ground planes.

points = [
    [0.0, 0],
    [100e-3, 0.0],
]
edb.modeler.create_trace(points, "TOP", width=1e-3)
points = [[0.0, 1e-3], [0.0, 10e-3], [100e-3, 10e-3], [100e-3, 1e-3], [0.0, 1e-3]]
edb.modeler.create_polygon(points, "TOP")

points = [[0.0, -1e-3], [0.0, -10e-3], [100e-3, -10e-3], [100e-3, -1e-3], [0.0, -1e-3]]
edb.modeler.create_polygon(points, "TOP")

#######################################
# Create vias with parametric positions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create vias with parametric positions.

edb.padstacks.create("MyVia")
edb.padstacks.place([5e-3, 5e-3], "MyVia")
edb.padstacks.place([15e-3, 5e-3], "MyVia")
edb.padstacks.place([35e-3, 5e-3], "MyVia")
edb.padstacks.place([45e-3, 5e-3], "MyVia")
edb.padstacks.place([5e-3, -5e-3], "MyVia")
edb.padstacks.place([15e-3, -5e-3], "MyVia")
edb.padstacks.place([35e-3, -5e-3], "MyVia")
edb.padstacks.place([45e-3, -5e-3], "MyVia")


#######################################
# Geometry Plot
# ~~~~~~~~~~~~~
#
edb.nets.plot(None, color_by_net=True)

#######################################
# Stackup Plot
# ~~~~~~~~~~~~
#
edb.stackup.plot(plot_definitions="MyVia")


####################
# Save and close EDB
# ~~~~~~~~~~~~~~~~~~
# Save and close EDB.

if edb:
    edb.save_edb()
    edb.close_edb()
print("EDB saved correctly to {}. You can import in AEDT.".format(aedb_path))
end = time.time() - start
print(end)
