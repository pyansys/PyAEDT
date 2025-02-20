"""
EDB: fully parametrized CPWG design
-----------------------------------
This example shows how you can use HFSS 3D Layout to create a parametric design
for a CPWG (coplanar waveguide with ground).
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Peform required imports. Importing the ``Hfss3dlayout`` object initializes it
# on version 2023 R2.

import pyaedt
import os
import numpy as np

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. The default is ``False``.

non_graphical = False

###############################################################################
# Launch EDB
# ~~~~~~~~~~
# Launch EDB.

aedb_path = os.path.join(pyaedt.generate_unique_folder_name(), pyaedt.generate_unique_name("pcb") + ".aedb")
print(aedb_path)
edbapp = pyaedt.Edb(edbpath=aedb_path, edbversion="2023.2")

###############################################################################
# Define parameters
# ~~~~~~~~~~~~~~~~~
# Define parameters.

params = {"$ms_width": "0.4mm",
          "$ms_clearance": "0.3mm",
          "$ms_length": "20mm",
          }
for par_name in params:
    edbapp.add_project_variable(par_name, params[par_name])

###############################################################################
# Create stackup
# ~~~~~~~~~~~~~~
# Create a symmetric stackup.

edbapp.stackup.create_symmetric_stackup(2)
edbapp.stackup.plot()

###############################################################################
# Draw planes
# ~~~~~~~~~~~
# Draw planes.

plane_lw_pt = ["0mm", "-3mm"]
plane_up_pt = ["$ms_length", "3mm"]

top_layer_obj = edbapp.modeler.create_rectangle("TOP", net_name="gnd",
                                                        lower_left_point=plane_lw_pt,
                                                        upper_right_point=plane_up_pt)
bot_layer_obj = edbapp.modeler.create_rectangle("BOTTOM", net_name="gnd",
                                                        lower_left_point=plane_lw_pt,
                                                        upper_right_point=plane_up_pt)
layer_dict = {"TOP": top_layer_obj,
              "BOTTOM": bot_layer_obj}

###############################################################################
# Draw trace
# ~~~~~~~~~~
# Draw a trace.

trace_path = [["0", "0"], ["$ms_length", "0"]]
edbapp.modeler.create_trace(trace_path,
                                    layer_name="TOP",
                                    width="$ms_width",
                                    net_name="sig",
                                    start_cap_style="Flat",
                                    end_cap_style="Flat"
                                    )

###############################################################################
# Create trace to plane clearance
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a trace to the plane clearance.

poly_void = edbapp.modeler.create_trace(trace_path, layer_name="TOP", net_name="gnd",
                                                width="{}+2*{}".format("$ms_width", "$ms_clearance"),
                                                start_cap_style="Flat",
                                                end_cap_style="Flat")
edbapp.modeler.add_void(layer_dict["TOP"], poly_void)

###############################################################################
# Create ground via padstack and place ground stitching vias
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a ground via padstack and place ground stitching vias.

edbapp.padstacks.create(padstackname="GVIA",
                                     holediam="0.3mm",
                                     paddiam="0.5mm",
                                     )

yloc_u = "$ms_width/2+$ms_clearance+0.25mm"
yloc_l = "-$ms_width/2-$ms_clearance-0.25mm"

for i in np.arange(1, 20):
    edbapp.padstacks.place([str(i) + "mm", yloc_u], "GVIA", net_name="GND")
    edbapp.padstacks.place([str(i) + "mm", yloc_l], "GVIA", net_name="GND")

###############################################################################
# Save and close EDB
# ~~~~~~~~~~~~~~~~~~
# Save and close EDB.

edbapp.save_edb()
edbapp.close_edb()

###############################################################################
# Open EDB in AEDT
# ~~~~~~~~~~~~~~~~
# Open EDB in AEDT.

h3d = pyaedt.Hfss3dLayout(projectname=aedb_path, specified_version="2023.2",
                          non_graphical=non_graphical, new_desktop_session=True)

###############################################################################
# Create wave ports
# ~~~~~~~~~~~~~~~~~
# Create wave ports.

h3d.create_edge_port("line_3", 0, iswave=True, wave_vertical_extension=10, wave_horizontal_extension=10)
h3d.create_edge_port("line_3", 2, iswave=True, wave_vertical_extension=10, wave_horizontal_extension=10)

###############################################################################
# Edit airbox extents
# ~~~~~~~~~~~~~~~~~~~
# Edit airbox extents.

h3d.edit_hfss_extents(air_vertical_positive_padding="10mm",
                      air_vertical_negative_padding="1mm")

###############################################################################
# Create setup
# ~~~~~~~~~~~~
# Create an HFSS simulation setup.

setup = h3d.create_setup()
setup["MaxPasses"]=2
setup["AdaptiveFrequency"]="3GHz"
setup["SaveAdaptiveCurrents"]=True
h3d.create_linear_count_sweep(
    setupname=setup.name,
    unit="GHz",
    freqstart=0,
    freqstop=5,
    num_of_freq_points=1001,
    sweepname="sweep1",
    sweep_type="Interpolating",
    interpolation_tol_percent=1,
    interpolation_max_solutions=255,
    save_fields=False,
    use_q3d_for_dc=False,
)

###############################################################################
# Plot layout
# ~~~~~~~~~~~
# Plot layout

h3d.modeler.edb.nets.plot(None, None, color_by_net=True)

cp_name = h3d.modeler.clip_plane()

h3d.save_project()

###############################################################################
# Start HFSS solver
# ~~~~~~~~~~~~~~~~~
# Start the HFSS solver by uncommenting the ``h3d.analyze()`` command.

h3d.analyze()

# Save AEDT
aedt_path = aedb_path.replace(".aedb", ".aedt")
h3d.logger.info("Your AEDT project is saved to {}".format(aedt_path))
solutions = h3d.get_touchstone_data()[0]
solutions.log_x = False
solutions.plot()

h3d.post.create_fieldplot_cutplane(cp_name, "Mag_E", h3d.nominal_adaptive, intrinsincDict={"Freq":"3GHz", "Phase":"0deg"})

# Release AEDT.
h3d.release_desktop()

