"""
EDB: post-layout parameterization
---------------------------------
This example shows you how to parameterize the signal net in post-layout.
"""

###############################################################################
# Define input parameters
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
signal_net_name = "DDR4_ALERT3"
coplanar_plane_net_name = "1V0"  # Specify coplanar plane net name for adding clearance
layers = ["16_Bottom"]  # Specify layers to be parameterized

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
import os
import tempfile
import pyaedt

from pyaedt import downloads
from pyaedt import Edb

temppath =  pyaedt.generate_unique_folder_name()

###############################################################################
# Download and open example layout file in edb format
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
edb_fpath = pyaedt.downloads.download_file('edb/ANSYS-HSD_V1.aedb',destination=temppath)
appedb = Edb(edb_fpath, edbversion="2023.2")

###############################################################################
# Cutout
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
appedb.cutout([signal_net_name], [coplanar_plane_net_name, "GND"],
              remove_single_pin_components=True)

###############################################################################
# Get all trace segments from the signal net
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
net = appedb.nets[signal_net_name]
trace_segments = []
for p in net.primitives:
    if p.layer_name not in layers:
        continue
    if not p.type == "Path":
        continue
    trace_segments.append(p)

###############################################################################
# Create and assign delta w variable per layer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
for p in trace_segments:
    vname = f"{p.net_name}_{p.layer_name}_dw"
    if vname not in appedb.variables:
        appedb[vname] = "0mm"
    new_w = f"{p.width}+{vname}"
    p.width = new_w

###############################################################################
# Delete existing clearance
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
for p in trace_segments:
    for g in appedb.modeler.get_polygons_by_layer(p.layer_name, coplanar_plane_net_name):
        for v in g.voids:
            if p.is_intersecting(v):
                v.delete()

###############################################################################
# Create and assign clearance variable per layer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
for p in trace_segments:
    clr = f"{p.net_name}_{p.layer_name}_clr"
    if clr not in appedb.variables:
        appedb[clr] = "0.5mm"
    path = p.get_center_line()
    for g in appedb.modeler.get_polygons_by_layer(p.layer_name, coplanar_plane_net_name):
        void = appedb.modeler.create_trace(path, p.layer_name, f"{p.width}+{clr}*2")
        g.add_void(void)

###############################################################################
# Plot
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
appedb.nets.plot(layers=layers[0], size=2000)

###############################################################################
# Save and close Edb
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

save_edb_fpath = os.path.join(temppath, pyaedt.generate_unique_name("post_layout_parameterization") + ".aedb")
appedb.save_edb_as(save_edb_fpath)
print("Edb is saved to ", save_edb_fpath)
appedb.close_edb()
