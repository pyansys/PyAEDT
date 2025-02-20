"""
Circuit: automatic report creation
----------------------------------
This example shows how you can use PyAEDT to create reports automatically using a JSON file.
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports and set the local path to the path for PyAEDT.

# sphinx_gallery_thumbnail_path = 'Resources/spectrum_plot.png'
import os

import pyaedt

# Set local path to path for PyAEDT
temp_folder = pyaedt.generate_unique_folder_name()
project_path = pyaedt.downloads.download_custom_reports(destination=temp_folder)

###############################################################################
# Launch AEDT
# ~~~~~~~~~~~
# Launch AEDT 2023 R2 in graphical mode. This example uses SI units.

desktopVersion = "2023.2"

##########################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.
# The Boolean parameter ``new_thread`` defines whether to create a new instance
# of AEDT or try to connect to an existing instance of it.

non_graphical = False
NewThread = True

###############################################################################
# Launch AEDT with Circuit
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT with Circuit. The :class:`pyaedt.Desktop` class initializes AEDT
# and starts the specified version in the specified mode.

cir = pyaedt.Circuit(projectname=os.path.join(project_path, 'CISPR25_Radiated_Emissions_Example23R1.aedtz'),
                     non_graphical=non_graphical,
                     specified_version=desktopVersion,
                     new_desktop_session=True
                     )

###############################################################################
# Create spectrum report
# ~~~~~~~~~~~~~~~~~~~~~~
# Create a spectrum report. You can use a JSON file to create a simple setup
# or a fully customized one. The following code creates a simple setup and changes
# the JSON file to customize it. In a spectrum report, you can add limitilines and
# notes and edit axes, the grid, and the legend. You can create custom reports
# in non-graphical mode in AEDT 2023 R2 and later.

report1 = cir.post.create_report_from_configuration(os.path.join(project_path,'Spectrum_CISPR_Basic.json'))

if not non_graphical:
    report1_full = cir.post.create_report_from_configuration(os.path.join(project_path,'Spectrum_CISPR_Custom.json'))

###############################################################################
# Create transient report
# ~~~~~~~~~~~~~~~~~~~~~~~
# Create a transient report. You can read and modify the JSON file
# before running the script. The following code modifies the traces
# before generating the report. You can create custom reports in non-graphical
# mode in AEDT 2023 R2 and later.

if non_graphical:
    props = pyaedt.data_handler.json_to_dict(os.path.join(project_path, 'Transient_CISPR_Basic.json'))
else:
    props = pyaedt.data_handler.json_to_dict(os.path.join(project_path, 'Transient_CISPR_Custom.json'))

report2 = cir.post.create_report_from_configuration(input_dict=props, solution_name="NexximTransient")
props["expressions"] = {"V(Battery)": {}, "V(U1_VDD)": {}}
props["plot_name"] = "Battery Voltage"
report3 = cir.post.create_report_from_configuration(input_dict=props, solution_name="NexximTransient")

###############################################################################
# Create eye diagram
# ~~~~~~~~~~~~~~~~~~
# Create an eye diagram. If the JSON file contains an eye mask, you can create
# an eye diagram and fully customize it. You can create custom reports in
# non-graphical mode in AEDT 2023 R2 and later.

report4 = cir.post.create_report_from_configuration(os.path.join(project_path, 'EyeDiagram_CISPR_Basic.json'))

if not non_graphical:
    report4_full = cir.post.create_report_from_configuration(os.path.join(project_path, 'EyeDiagram_CISPR_Custom.json'))

if not non_graphical:
    cir.post.export_report_to_jpg(cir.working_directory, report4.plot_name)

################################################
# This is how the spectrum looks like
# .. image:: Resources/spectrum_plot.png

###############################################################################
# Save project and close AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Save the project and close AEDT.

cir.save_project()
print("Project Saved in {}".format(cir.project_path))
cir.release_desktop()
