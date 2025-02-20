"""
HFSS: component antenna array
-----------------------------
This example shows how you can use PyAEDT to create an example using a 3D component file. It sets up
the analysis, solves it, and uses postprocessing functions to create plots using Matplotlib and
PyVista without opening the HFSS user interface. This examples runs only on Windows using CPython.
"""
##########################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import ansys.aedt.core
from ansys.aedt.core.generic.farfield_visualization import FfdSolutionData

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.2"

##########################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

##########################################################
# Download 3D component
# ~~~~~~~~~~~~~~~~~~~~~
# Download the 3D component that is needed to run the example.
example_path = ansys.aedt.core.downloads.download_3dcomponent()

##########################################################
# Launch HFSS and save project
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Launch HFSS and save the project.
project_name = ansys.aedt.core.generate_unique_project_name(project_name="array")
hfss = ansys.aedt.core.Hfss(project=project_name,
                   version=aedt_version,
                   design="Array_Simple",
                   non_graphical=non_graphical,
                   new_desktop=True)

print("Project name " + project_name)

##########################################################
# Read array definition from JSON file
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Read the array definition from a JSON file. A JSON file
# can contain all information needed to import and set up a
# full array in HFSS.
# 
# If a 3D component is not available in the design, it is loaded
# into the dictionary from the path that you specify. The following
# code edits the dictionary to point to the location of the A3DCOMP file.

dict_in = ansys.aedt.core.general_methods.read_json(os.path.join(example_path, "array_simple.json"))
dict_in["Circ_Patch_5GHz1"] = os.path.join(example_path, "Circ_Patch_5GHz.a3dcomp")
dict_in["cells"][(3, 3)] = {"name": "Circ_Patch_5GHz1"}
array = hfss.add_3d_component_array_from_json(dict_in)

##########################################################
# Modify cells
# ~~~~~~~~~~~~
# Rotate corner elements.

array.cells[0][0].rotation = 90
array.cells[0][2].rotation = 90
array.cells[2][0].rotation = 90
array.cells[2][2].rotation = 90

##########################################################
# Set up simulation
# ~~~~~~~~~~~~~~~~~
# Set up a simulation and analyze it.

setup = hfss.create_setup()
setup.props["Frequency"] = "5GHz"
setup.props["MaximumPasses"] = 3

hfss.analyze(cores=4)
hfss.save_project()

##########################################################
# Get far field data
# ~~~~~~~~~~~~~~~~~~
# Get far field data. After the simulation completes, the far
# field data is generated port by port and stored in a data class.

ffdata = hfss.get_antenna_data(setup=hfss.nominal_adaptive, sphere="Infinite Sphere1")

##########################################################
# Generate contour plot
# ~~~~~~~~~~~~~~~~~~~~~
# Generate a contour plot. You can define the Theta scan
# and Phi scan.

ffdata.farfield_data.plot_contour(quantity='RealizedGain',
                                  title='Contour at {}Hz'.format(ffdata.farfield_data.frequency))

##########################################################
# Release AEDT
# ~~~~~~~~~~~~
# Release AEDT.
# Far field post-processing can be performed without AEDT because the data is stored.

eep_file = ffdata.metadata_file
working_directory = hfss.working_directory

hfss.release_desktop()

##########################################################
# Load far field data
# ~~~~~~~~~~~~~~~~~~~
# Load far field data stored.

ffdata = FfdSolutionData(input_file=eep_file)

##########################################################
# Generate contour plot
# ~~~~~~~~~~~~~~~~~~~~~
# Generate a contour plot. You can define the Theta scan
# and Phi scan.

ffdata.plot_contour(quantity='RealizedGain', title='Contour at {}Hz'.format(ffdata.frequency))

##########################################################
# Generate 2D cutout plots
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Generate 2D cutout plots. You can define the Theta scan
# and Phi scan.

ffdata.plot_cut(quantity='RealizedGain', primary_sweep='theta', secondary_sweep_value=[-180, -75, 75],
                title='Azimuth at {}Hz'.format(ffdata.frequency), quantity_format="dB10")

ffdata.plot_cut(quantity='RealizedGain', primary_sweep="phi", secondary_sweep_value=30, title='Elevation',
                quantity_format="dB10")

##########################################################
# Generate 3D plots
# ~~~~~~~~~~~~~~~~~
# Generate 3D plots. You can define the Theta scan and Phi scan.

# ffdata.plot_3d(quantity='RealizedGain',
#                output_file=os.path.join(working_directory, "Image.jpg"),
#                show=False)
