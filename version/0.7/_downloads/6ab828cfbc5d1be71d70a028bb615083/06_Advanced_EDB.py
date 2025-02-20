"""
EDB: parametric via creation
----------------------------
This example shows how you can use EDB to create a layout.
"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import numpy as np
import pyaedt


aedb_path = os.path.join(pyaedt.generate_unique_folder_name(), pyaedt.generate_unique_name("via_opt") + ".aedb")

###############################################################################
# Create stackup
# ~~~~~~~~~~~~~~
# The ``StackupSimple`` class creates a stackup based on few inputs. This stackup
# is used later.


###############################################################################
# Create ground plane
# ~~~~~~~~~~~~~~~~~~~
# Create a ground plane on specific layers.

def _create_ground_planes(edb, layers):
    plane = edb.modeler.Shape("rectangle", pointA=["-3mm", "-3mm"], pointB=["3mm", "3mm"])
    for i in layers:
        edb.modeler.create_polygon(plane, i, net_name="GND")


##################################################################################
# Create EDB
# ~~~~~~~~~~
# Create EDB. If the path doesn't exist, PyAEDT automatically generates a new AEDB folder.

edb = pyaedt.Edb(edbpath=aedb_path, edbversion="2023.2")

##################################################################################
# Create stackup layers
# ~~~~~~~~~~~~~~~~~~~~~
# Create stackup layers.

layout_count = 12
diel_material_name = "FR4_epoxy"
diel_thickness = "0.15mm"
cond_thickness_outer = "0.05mm"
cond_thickness_inner = "0.017mm"
soldermask_thickness = "0.05mm"
trace_in_layer = "TOP"
trace_out_layer = "L10"
gvia_num = 10
gvia_angle = 30
edb.stackup.create_symmetric_stackup(layer_count=layout_count, inner_layer_thickness=cond_thickness_inner,
                                     outer_layer_thickness=cond_thickness_outer,
                                     soldermask_thickness=soldermask_thickness, dielectric_thickness=diel_thickness,
                                     dielectric_material=diel_material_name)


##################################################################################
# Create variables
# ~~~~~~~~~~~~~~~~
# Create all variables. If a variable has a ``$`` prefix, it is a project variable.
# Otherwise, is a design variable.

giva_angle_rad = gvia_angle / 180 * np.pi

edb["$via_hole_size"] = "0.3mm"
edb["$antipaddiam"] = "0.7mm"
edb["$paddiam"] = "0.5mm"
edb.add_design_variable("via_pitch", "1mm", is_parameter=True)
edb.add_design_variable("trace_in_width", "0.2mm", is_parameter=True)
edb.add_design_variable("trace_out_width", "0.1mm", is_parameter=True)

##################################################################################
# Create definitions
# ~~~~~~~~~~~~~~~~~~
# Create two definitions, one for the ground and one for the signal. The definitions
# are parametric.

edb.padstacks.create(padstackname="SVIA",
                     holediam="$via_hole_size",
                     antipaddiam="$antipaddiam",
                     paddiam="$paddiam",
                     start_layer=trace_in_layer,
                     stop_layer=trace_out_layer
)
edb.padstacks.create(padstackname="GVIA", holediam="0.3mm", antipaddiam="0.7mm", paddiam="0.5mm")

##################################################################################
# Place padstack for signal
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Place the padstack for the signal.

edb.padstacks.place([0, 0], "SVIA", net_name="RF")

##################################################################################
# Place padstack for ground
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Place the padstack for the  ground. A loop iterates and places multiple ground
# vias on different positions.

gvia_num_side = gvia_num / 2

if gvia_num_side % 2:

    # Even number of ground vias on each side
    edb.padstacks.place(["via_pitch", 0], "GVIA", net_name="GND")
    edb.padstacks.place(["via_pitch*-1", 0], "GVIA", net_name="GND")
    for i in np.arange(1, gvia_num_side / 2):
        xloc = "{}*{}".format(np.cos(giva_angle_rad * i), "via_pitch")
        yloc = "{}*{}".format(np.sin(giva_angle_rad * i), "via_pitch")
        edb.padstacks.place([xloc, yloc], "GVIA", net_name="GND")
        edb.padstacks.place([xloc, yloc + "*-1"], "GVIA", net_name="GND")

        edb.padstacks.place([xloc + "*-1", yloc], "GVIA", net_name="GND")
        edb.padstacks.place([xloc + "*-1", yloc + "*-1"], "GVIA", net_name="GND")
else:

    # Odd number of ground vias on each side
    for i in np.arange(0, gvia_num_side / 2):
        xloc = "{}*{}".format(np.cos(giva_angle_rad * (i + 0.5)), "via_pitch")
        yloc = "{}*{}".format(np.sin(giva_angle_rad * (i + 0.5)), "via_pitch")
        edb.padstacks.place([xloc, yloc], "GVIA", net_name="GND")
        edb.padstacks.place([xloc, yloc + "*-1"], "GVIA", net_name="GND")

        edb.padstacks.place([xloc + "*-1", yloc], "GVIA", net_name="GND")
        edb.padstacks.place([xloc + "*-1", yloc + "*-1"], "GVIA", net_name="GND")

##################################################################################
# Generate traces
# ~~~~~~~~~~~~~~~
# Generate and place parametric traces.

edb.modeler.create_trace(
    [[0, 0], [0, "-3mm"]], layer_name=trace_in_layer, net_name="RF", width="trace_in_width", start_cap_style="Flat", end_cap_style="Flat"
)

edb.modeler.create_trace(
    [[0, 0], [0, "3mm"]],
    layer_name=trace_out_layer,
    net_name="RF",
    width="trace_out_width",
    start_cap_style="Flat",
    end_cap_style="Flat",
)

##################################################################################
# Generate ground layers
# ~~~~~~~~~~~~~~~~~~~~~~
# Generate and place ground layers.

ground_layers = [i for i in edb.stackup.signal_layers.keys()]
ground_layers.remove(trace_in_layer)
ground_layers.remove(trace_out_layer)
_create_ground_planes(edb=edb, layers=ground_layers)

##################################################################################
# Plot Layout
# ~~~~~~~~~~~
# Generate and plot the layout.

#edb.nets.plot(layers=["TOP", "L10"])
edb.stackup.plot(plot_definitions=["GVIA", "SVIA"])


##################################################################################
# Save EDB and close
# ~~~~~~~~~~~~~~~~~~
# Save EDB and close.

edb.save_edb()
edb.close_edb()

print("aedb Saved in {}".format(aedb_path))
