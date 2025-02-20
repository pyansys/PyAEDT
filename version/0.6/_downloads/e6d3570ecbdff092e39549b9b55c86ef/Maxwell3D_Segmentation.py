"""
Maxwell 3D: magnet segmentation
-------------------------------
This example shows how you can use PyAEDT to segment magnets of an electric motor.
The method is valid and usable for any object the user would like to segment.
"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

from pyaedt import downloads
from pyaedt import generate_unique_folder_name
from pyaedt import Maxwell3d

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

#################################################################################
# Download .aedt file example
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Set local temporary folder to export the .aedt file to.
temp_folder = generate_unique_folder_name()
aedt_file = downloads.download_file("object_segmentation", "Motor3D_obj_segments.aedt", temp_folder)

##################################################################################
# Launch Maxwell 3D
# ~~~~~~~~~~~~~~~~~
# Launch Maxwell 3D.

m3d = Maxwell3d(projectname=aedt_file,
                specified_version="2023.2",
                new_desktop_session=True,
                non_graphical=non_graphical)

##################################################################################
# Create object to access 3D modeler
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create the object ``mod3D`` to access the 3D modeler easily.

modeler = m3d.modeler

##################################################################################
# Segment first magnet by specifying the number of segments
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Select first magnet to segment by specifying the number of segments.
# The method accepts in input either the list of magnets names to segment or
# magnets ids or the magnet object :class:`pyaedt.modeler.cad.object3d.Object3d`.
# ``apply_mesh_sheets`` is enabled which means that the mesh sheets will
# be applied in the geometry too.
# In this specific case we give as input the name of the magnet.

segments_number = 5
object_name = "PM_I1"
sheets_1 = modeler.objects_segmentation(object_name, segments_number=segments_number, apply_mesh_sheets=True)

##################################################################################
# Segment second magnet by specifying the number of segments
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Select second magnet to segment by specifying the number of segments.
# In this specific case we give as input the id of the magnet.

segments_number = 4
object_name = "PM_I1_1"
magnet_id = [obj.id for obj in modeler.object_list if obj.name == object_name][0]
sheets_2 = modeler.objects_segmentation(magnet_id, segments_number=segments_number, apply_mesh_sheets=True)

##################################################################################
# Segment third magnet by specifying the segmentation thickness
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Select third magnet to segment by specifying the segmentation thickness.
# In this specific case we give as input the magnet object of type :class:`pyaedt.modeler.cad.object3d.Object3d`.

segmentation_thickness = 1
object_name = "PM_O1"
magnet = [obj for obj in modeler.object_list if obj.name == object_name][0]
sheets_3 = modeler.objects_segmentation(magnet, segmentation_thickness=segmentation_thickness, apply_mesh_sheets=True)

##################################################################################
# Segment fourth magnet by specifying the number of segments
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Select fourth magnet to segment by specifying the number of segments.
# In this specific case we give as input the name of the magnet and we disable the mesh sheets.

object_name = "PM_O1_1"
segments_number = 10
sheets_4 = modeler.objects_segmentation(object_name, segments_number=segments_number)

###################################################################################
# Save project and close AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Save the project and close AEDT.

m3d.save_project()
m3d.release_desktop()
