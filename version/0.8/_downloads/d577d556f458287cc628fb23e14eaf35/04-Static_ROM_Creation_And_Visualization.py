"""
Twin Builder: static ROM creation and simulation (2023 R2 beta)
---------------------------------------------------------------
This example shows how you can use PyAEDT to create a static ROM in Twin Builder
and run a Twin Builder time-domain simulation.

.. note::
    This example uses functionality only available in Twin Builder 2023 R2 and later.
    For 2023 R2, the build date must be 8/7/2022 or later. 
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import math
import shutil
import matplotlib.pyplot as plt
from pyaedt import TwinBuilder
from pyaedt import generate_unique_project_name
from pyaedt import generate_unique_folder_name
from pyaedt import downloads
from pyaedt import settings

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

###############################################################################
# Select version and set launch options
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Select the Twin Builder version and set launch options. The following code
# launches Twin Builder 2023 R2 in graphical mode.
#
# You can change the Boolean parameter ``non_graphical`` to ``True`` to launch
# Twin Builder in non-graphical mode. You can also change the Boolean parameter
# ``new_thread`` to ``False`` to launch Twin Builder in an existing AEDT session
# if one is running.

non_graphical = False
new_thread = True

###############################################################################
# Set up input data
# ~~~~~~~~~~~~~~~~~
# Define needed file name

source_snapshot_data_zipfilename = "Ex1_Fluent_StaticRom.zip"
source_build_conf_file = "SROMbuild.conf"
source_props_conf_file = "SROM_props.conf"

# Download data from example_data repository
source_data_folder = downloads.download_twin_builder_data(source_snapshot_data_zipfilename, True)
source_data_folder = downloads.download_twin_builder_data(source_build_conf_file, True)
source_data_folder = downloads.download_twin_builder_data(source_props_conf_file, True)

# Uncomment the following line for local testing 
# source_data_folder = "D:\\Scratch\\TempStatic"

data_folder = os.path.join(source_data_folder, "Ex04")

# Unzip training data and config file
downloads.unzip(os.path.join(source_data_folder, source_snapshot_data_zipfilename), data_folder)
shutil.copyfile(os.path.join(source_data_folder, source_build_conf_file),
                os.path.join(data_folder, source_build_conf_file))
shutil.copyfile(os.path.join(source_data_folder, source_props_conf_file),
                os.path.join(data_folder, source_props_conf_file))

###############################################################################
# Launch Twin Builder and build ROM component
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Launch Twin Builder using an implicit declaration and add a new design with
# a default setup for building the static ROM component.

tb = TwinBuilder(projectname=generate_unique_project_name(), specified_version=aedt_version,
                 non_graphical=non_graphical, new_desktop_session=new_thread)

# Switch the current desktop configuration and the schematic environment to "Twin Builder".
# The Static ROM feature is only available with a twin builder license.
# This and the restoring section at the end are not needed if the desktop is already configured as "Twin Builder".
current_desktop_config = tb._odesktop.GetDesktopConfiguration()
current_schematic_environment = tb._odesktop.GetSchematicEnvironment()
tb._odesktop.SetDesktopConfiguration("Twin Builder")
tb._odesktop.SetSchematicEnvironment(1)

# Get the static ROM builder object
rom_manager = tb._odesign.GetROMManager()
static_rom_builder = rom_manager.GetStaticROMBuilder()

# Build the static ROM with specified configuration file
confpath = os.path.join(data_folder, source_build_conf_file)
static_rom_builder.Build(confpath.replace('\\', '/'))

# Test if ROM was created successfully
static_rom_path = os.path.join(data_folder, 'StaticRom.rom')
if os.path.exists(static_rom_path):
    tb.logger.info("Built intermediate rom file successfully at: %s", static_rom_path)
else:
    tb.logger.error("Intermediate rom file not found at: %s", static_rom_path)

# Create the ROM component definition in Twin Builder
rom_manager.CreateROMComponent(static_rom_path.replace('\\', '/'), 'staticrom')

###############################################################################
# Create schematic
# ~~~~~~~~~~~~~~~~
# Place components to create a schematic.

# Define the grid distance for ease in calculations
G = 0.00254

# Place a dynamic ROM component
rom1 = tb.modeler.schematic.create_component("ROM1", "", "staticrom", [40 * G, 25 * G])

# Place two excitation sources
source1 = tb.modeler.schematic.create_periodic_waveform_source(None, "SINE", 2.5, 0.01, 0, 7.5, 0, [20 * G, 29 * G])
source2 = tb.modeler.schematic.create_periodic_waveform_source(None, "SINE", 50, 0.02, 0, 450, 0, [20 * G, 25 * G])

# Connect components with wires

tb.modeler.schematic.create_wire([[22 * G, 29 * G], [33 * G, 29 * G]])
tb.modeler.schematic.create_wire([[22 * G, 25 * G], [30 * G, 25 * G], [30 * G, 28 * G], [33 * G, 28 * G]])

# Enable storage of views

rom1.set_property("store_snapshots", 1)
rom1.set_property("view1_storage_period", "10s")
rom1.set_property("view2_storage_period", "10s")

# Zoom to fit the schematic
tb.modeler.zoom_to_fit()

###############################################################################
# Parametrize transient setup
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Parametrize the default transient setup by setting the end time.

tb.set_end_time("300s")
tb.set_hmin("1s")
tb.set_hmax("1s")

###############################################################################
# Solve transient setup
# ~~~~~~~~~~~~~~~~~~~~~
# Solve the transient setup. Skipping in case of documentation build.

if os.getenv("PYAEDT_DOC_GENERATION", "False") != "1":
    tb.analyze_setup("TR")

###############################################################################
# Get report data and plot using Matplotlib
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get report data and plot it using Matplotlib. The following code gets and plots
# the values for the voltage on the pulse voltage source and the values for the
# output of the dynamic ROM.
if os.getenv("PYAEDT_DOC_GENERATION", "False") != "1":
    e_value = "ROM1.outfield_mode_1"
    x = tb.post.get_solution_data(e_value, "TR", "Time")
    x.plot()
    e_value = "ROM1.outfield_mode_2"
    x = tb.post.get_solution_data(e_value, "TR", "Time")
    x.plot()
    e_value = "SINE1.VAL"
    x = tb.post.get_solution_data(e_value, "TR", "Time")
    x.plot()
    e_value = "SINE2.VAL"
    x = tb.post.get_solution_data(e_value, "TR", "Time")
    x.plot()


###############################################################################
# Close Twin Builder
# ~~~~~~~~~~~~~~~~~~
# After the simulation is completed, you can close Twin Builder or release it.
# All methods provide for saving the project before closing.

# Clean up the downloaded data
shutil.rmtree(source_data_folder)

# Restore earlier desktop configuration and schematic environment
tb._odesktop.SetDesktopConfiguration(current_desktop_config)
tb._odesktop.SetSchematicEnvironment(current_schematic_environment)

tb.release_desktop()
