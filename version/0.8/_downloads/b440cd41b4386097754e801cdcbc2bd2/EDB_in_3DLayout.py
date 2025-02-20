"""
HFSS 3D Layout: PCB and EDB in 3D layout
----------------------------------------
This example shows how you can use HFSS 3D Layout combined with EDB to
interact with a 3D layout.
"""


import os
import tempfile
import pyaedt

tmpfold = tempfile.gettempdir()
temp_folder = os.path.join(tmpfold, pyaedt.generate_unique_name("Example"))
if not os.path.exists(temp_folder):
    os.makedirs(temp_folder)
print(temp_folder)

###############################################################################
# Copy example into temporary folder
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Copy an example into the temporary folder.

targetfile = pyaedt.downloads.download_aedb()
print(targetfile)
aedt_file = targetfile[:-12] + "aedt"

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False
NewThread = True

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

###############################################################################
# Initialize AEDT and launch HFSS 3D Layout
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Initialize AEDT and launch HFSS 3D Layout.
# The ``h3d`` object contains the :class:`pyaedt.Edb` class query methods.

d = pyaedt.launch_desktop(aedt_version, non_graphical, NewThread)
if os.path.exists(aedt_file):
    os.remove(aedt_file)
h3d = pyaedt.Hfss3dLayout(targetfile)
h3d.save_project(os.path.join(temp_folder, "edb_demo.aedt"))

###############################################################################
# Print boundaries
# ~~~~~~~~~~~~~~~~
# Print boundaries from the ``setups`` object.

h3d.boundaries

###############################################################################
# Hide all nets
# ~~~~~~~~~~~~~
# Hide all nets.

h3d.modeler.change_net_visibility(visible=False)

###############################################################################
# Show only two nets
# ~~~~~~~~~~~~~~~~~~
# Show only two specified nets.

h3d.modeler.change_net_visibility(["A0_GPIO", "A0_MUX"], visible=True)
edb = h3d.modeler.edb
edb.nets.plot(["A0_GPIO", "A0_MUX"])

###############################################################################
# Show all layers
# ~~~~~~~~~~~~~~~
# Show all layers.

for layer in h3d.modeler.layers.all_signal_layers:
    layer.is_visible = True

###############################################################################
# Change layer color
# ~~~~~~~~~~~~~~~~~~
# Change the layer color.

layer = h3d.modeler.layers.layers[h3d.modeler.layers.layer_id("TOP")]
layer.set_layer_color(0, 255, 0)
h3d.modeler.fit_all()

###############################################################################
# Disable component visibility
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Disable component visibility for ``"TOP"`` and ``"BOTTOM"``.
# The :func:`pyaedt.modules.LayerStackup.Layer.update_stackup_layer` method
# applies modifications to the layout.

top = h3d.modeler.layers.layers[h3d.modeler.layers.layer_id("TOP")]
top.is_visible_component = False

bot = h3d.modeler.layers.layers[h3d.modeler.layers.layer_id("BOTTOM")]
bot.is_visible_component = False

###############################################################################
# Fit all
# ~~~~~~~
# Fit all so that you can visualize all.

h3d.modeler.fit_all()

###############################################################################
# Close AEDT
# ~~~~~~~~~~
# After the simulation completes, you can close AEDT or release it using the
# :func:`pyaedt.Desktop.release_desktop` method.
# All methods provide for saving the project before closing.

h3d.close_project()
d.release_desktop()
