"""
HFSS: Probe-fed patch antenna
---------------------------------------------------------
This example shows how to use the ``Stackup3D`` class
to create and analyze a patch antenna in HFSS.

Note that the HFSS 3D Layout interface may offer advantages for
laminate structures such as the patch antenna.
"""

###########################
# Perform  imports
# ~~~~~~~~~~~~~~~~~~

import os

import pyaedt
import tempfile
from pyaedt.modeler.advanced_cad.stackup_3d import Stackup3D

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. ``"PYAEDT_NON_GRAPHICAL"`` is set to ``False``
# to create this documentation.
#
# You can set ``non_graphical``  to ``True`` to view
# HFSS while the notebook cells are executed.

non_graphical = False
length_units = "mm"
freq_units = "GHz"

########################################################
# Create temporary working folder
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Use tempfile to create a temporary working folder. Project data
# is deleted after this example is run.
#
# To save the project data in another location, change
# the location of the project directory.
#

# tmpdir.cleanup() at the end of this notebook removes all
# project files and data.

tmpdir = tempfile.TemporaryDirectory(suffix="_aedt")
project_folder = tmpdir.name
proj_name = os.path.join(project_folder, "antenna")

#####################
# Launch HFSS
# -----------
#

hfss = pyaedt.Hfss(projectname=proj_name,
                   solution_type="Terminal",
                   designname="patch",
                   non_graphical=non_graphical,
                   new_desktop_session=True,
                   specified_version=aedt_version)

hfss.modeler.model_units = length_units

#####################################
# Create patch
# ------------
# Create the patch.
#

stackup = Stackup3D(hfss)
ground = stackup.add_ground_layer("ground", material="copper", thickness=0.035, fill_material="air")
dielectric = stackup.add_dielectric_layer("dielectric", thickness="0.5" + length_units, material="Duroid (tm)")
signal = stackup.add_signal_layer("signal", material="copper", thickness=0.035, fill_material="air")
patch = signal.add_patch(patch_length=9.57, patch_width=9.25,
                         patch_name="Patch", frequency=1E10)

stackup.resize_around_element(patch)
pad_length = [3, 3, 3, 3, 3, 3]  # Air bounding box buffer in mm.
region = hfss.modeler.create_region(pad_length, is_percentage=False)
hfss.assign_radiation_boundary_to_objects(region.name)

patch.create_probe_port(ground, rel_x_offset=0.485)
setup = hfss.create_setup(name="Setup1",
                          setup_type="HFSSDriven",
                          Frequency="10GHz")

setup.create_frequency_sweep(unit="GHz",
                             name="Sweep1",
                             start_frequency=8,
                             stop_frequency=12,
                             sweep_type="Interpolating")

hfss.save_project()
hfss.analyze()

###############################
# Plot S11
# ---------

plot_data = hfss.get_traces_for_plot()
report = hfss.post.create_report(plot_data)
solution = report.get_solution_data()
plt = solution.plot(solution.expressions)

###############################################################################
# Release AEDT
# ------------
# Release AEDT and clean up temporary folders and files.

hfss.release_desktop()
tmpdir.cleanup()
