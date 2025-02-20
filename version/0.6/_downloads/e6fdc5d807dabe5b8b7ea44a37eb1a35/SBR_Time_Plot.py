"""
SBR+: HFSS to SBR+ time animation
---------------------------------
This example shows how you can use PyAEDT to create an SBR+ time animation
and save it to a GIF file. This example works only on CPython.
"""

###############################################################################
# Perform required imports.
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Perform requried imports.

import os
from pyaedt import Hfss, downloads

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

###############################################################################
# Launch AEDT and load project
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT and load the project.

project_file = downloads.download_sbr_time()

hfss = Hfss(projectname=project_file, specified_version="2023.2", non_graphical=non_graphical, new_desktop_session=True)

hfss.analyze()

###############################################################################
# Get solution data
# ~~~~~~~~~~~~~~~~~
# Get solution data. After simulation is performed, you can load solutions
# in the ``solution_data`` object.

solution_data = hfss.post.get_solution_data(expressions=["NearEX", "NearEY", "NearEZ"],
                                            variations={"_u": ["All"], "_v": ["All"], "Freq": ["All"]},
                                            context="Near_Field",
                                            report_category="Near Fields")

###############################################################################
# Compute IFFT
# ~~~~~~~~~~~~
# Compute IFFT (Inverse Fast Fourier Transform).

t_matrix = solution_data.ifft("NearE", window=True)


###############################################################################
# Export IFFT to CSV file
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Export IFFT to a CSV file.

frames_list_file = solution_data.ifft_to_file(coord_system_center=[-0.15, 0, 0], db_val=True,
                                              csv_dir=os.path.join(hfss.working_directory, "csv"))

###############################################################################
# Plot scene
# ~~~~~~~~~~
# Plot the scene to create the time plot animation

hfss.post.plot_scene(frames_list=frames_list_file,
                     output_gif_path=os.path.join(hfss.working_directory, "animation.gif"),
                     norm_index=15,
                     dy_rng=35,
                     show=False, view="xy", zoom=1)

hfss.release_desktop()
