"""
General: configuration files
----------------------------
This example shows how you can use PyAEDT to export configuration files and re-use
them to import in a new project. A configuration file is supported by these applications:

* HFSS
* 2D Extractor and Q3D Extractor
* Maxwell
* Icepak (in AEDT)
* Mechanical (in AEDT)

The following sections are covered:

* Variables
* Mesh operations (except Icepak)
* Setup and optimetrics
* Material properties
* Object properties
* Boundaries and excitations

When a boundary is attached to a face, the tool tries to match it with a
``FaceByPosition`` on the same object name on the target design. If, for
any reason, this face position has changed or the object name in the target
design has changed, the boundary fails to apply.
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports from PyAEDT.

import os
import pyaedt

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. ``"PYAEDT_NON_GRAPHICAL"`` is needed to generate
# documentation only.
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = os.getenv("PYAEDT_NON_GRAPHICAL", "False").lower() in ("true", "1", "t")

###############################################################################
# Open project
# ~~~~~~~~~~~~
# Download the project, open it, and save it to the temporary folder.

project_full_name = pyaedt.downloads.download_icepak(pyaedt.generate_unique_folder_name(folder_name="Graphic_Card"))

ipk = pyaedt.Icepak(projectname=project_full_name, specified_version="2022.2",
                    new_desktop_session=True, non_graphical=non_graphical)
ipk.autosave_disable()

###############################################################################
# Create source blocks
# ~~~~~~~~~~~~~~~~~~~~
# Create a source block on the CPU and memories.

ipk.create_source_block(object_name="CPU", input_power="25W")
ipk.create_source_block(object_name=["MEMORY1", "MEMORY1_1"], input_power="5W")

###############################################################################
# Assign boundaries
# ~~~~~~~~~~~~~~~~~
# Assign the opening and grille.

region = ipk.modeler["Region"]
ipk.assign_openings(air_faces=region.bottom_face_x.id)
ipk.assign_grille(air_faces=region.top_face_x.id, free_area_ratio=0.8)

###############################################################################
# Create setup
# ~~~~~~~~~~~~
# Create the setup. Properties can be set up from the ``setup`` object
# with getters and setters. They don't have to perfectly match the property
# syntax.

setup1 = ipk.create_setup()
setup1["FlowRegime"] = "Turbulent"
setup1["Max Iterations"] = 5
setup1["Solver Type Pressure"] = "flex"
setup1["Solver Type Temperature"] = "flex"
ipk.save_project(r"C:\temp\Graphic_card.aedt")

###############################################################################
# Export project to step file
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Export the current project to the step file.

filename = ipk.design_name
file_path = os.path.join(ipk.working_directory, filename + ".step")
ipk.export_3d_model(file_name=filename, file_path=ipk.working_directory, file_format=".step", object_list=[],
                    removed_objects=[])

###############################################################################
# Export configuration files
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Export the configuration files. You can optionally disable the export and
# import sections.

conf_file = ipk.configurations.export_config()
ipk.close_project()

###############################################################################
# Create project
# ~~~~~~~~~~~~~~
# Create an Icepak project and import the step.

app = pyaedt.Icepak(projectname="new_proj_Ipk")
app.modeler.import_3d_cad(file_path)

###############################################################################
# Import and apply configuration file
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Import and apply the configuration file. You can apply all or part of the
# JSON file that you import using options in the ``configurations`` object.

out = app.configurations.import_config(conf_file)
app.configurations.results.global_import_success

###############################################################################
# Close project
# ~~~~~~~~~~~~~
# Close the project.

app.release_desktop()
