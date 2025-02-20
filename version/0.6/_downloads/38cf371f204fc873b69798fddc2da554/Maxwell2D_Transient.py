"""
Maxwell 2D: transient winding analysis
--------------------------------------
This example shows how you can use PyAEDT to create a project in Maxwell 2D
and run a transient simulation. It runs only on Windows using CPython.

The following libraries are required for the advanced postprocessing features
used in this example:

- `Matplotlib <https://pypi.org/project/matplotlib/>`_
- `Numpty <https://pypi.org/project/numpy/>`_
- `PyVista <https://pypi.org/project/pyvista/>`_

Install these libraries with:

.. code::

   pip install numpy pyvista matplotlib

"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import pyaedt

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

###############################################################################
# Insert Maxwell 2D design and save project
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Insert a Maxwell 2D design and save the project.

maxwell_2d = pyaedt.Maxwell2d(solution_type="TransientXY", specified_version="2023.2", non_graphical=non_graphical,
                              new_desktop_session=True, projectname=pyaedt.generate_unique_project_name())

###############################################################################
# Create rectangle and duplicate it
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a rectangle and duplicate it.

rect1 = maxwell_2d.modeler.create_rectangle([0, 0, 0], [10, 20], name="winding", matname="copper")
added = rect1.duplicate_along_line([14, 0, 0])
rect2 = maxwell_2d.modeler[added[0]]

###############################################################################
# Create air region
# ~~~~~~~~~~~~~~~~~
# Create an air region.

region = maxwell_2d.modeler.create_region([100, 100, 100, 100, 100, 100])

###############################################################################
# Assign windings and balloon
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Assigns windings to the sheets and a balloon to the air region.

maxwell_2d.assign_winding([rect1.name, rect2.name], name="PHA")
maxwell_2d.assign_balloon(region.edges)

###############################################################################
# Plot model
# ~~~~~~~~~~
# Plot the model.

maxwell_2d.plot(show=False, export_path=os.path.join(maxwell_2d.working_directory, "Image.jpg"), plot_air_objects=True)

###############################################################################
# Create setup
# ~~~~~~~~~~~~
# Create the transient setup.

setup = maxwell_2d.create_setup()
setup.props["StopTime"] = "0.02s"
setup.props["TimeStep"] = "0.0002s"
setup.props["SaveFieldsType"] = "Every N Steps"
setup.props["N Steps"] = "1"
setup.props["Steps From"] = "0s"
setup.props["Steps To"] = "0.002s"

###############################################################################
# Create rectangular plot
# ~~~~~~~~~~~~~~~~~~~~~~~
# Create a rectangular plot.

maxwell_2d.post.create_report(
    "InputCurrent(PHA)", domain="Time", primary_sweep_variable="Time", plotname="Winding Plot 1"
)

###############################################################################
# Solve model
# ~~~~~~~~~~~
# Solve the model.

maxwell_2d.analyze(use_auto_settings=False)

###############################################################################
# Create output and plot using PyVista
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create the output and plot it using PyVista.

cutlist = ["Global:XY"]
face_lists = rect1.faces
face_lists += rect2.faces
timesteps = [str(i * 2e-4) + "s" for i in range(11)]
id_list = [f.id for f in face_lists]

animatedGif = maxwell_2d.post.plot_animated_field(
    "Mag_B",
    id_list,
    "Surface",
    intrinsics={"Time": "0s"},
    variation_variable="Time",
    variation_list=timesteps,
    show=False,
    export_gif=False,
)
animatedGif.isometric_view = False
animatedGif.camera_position = [15, 15, 80]
animatedGif.focal_point = [15, 15, 0]
animatedGif.roll_angle = 0
animatedGif.elevation_angle = 0
animatedGif.azimuth_angle = 0
# Set off_screen to False to visualize the animation.
# animatedGif.off_screen = False
animatedGif.animate()

###############################################################################
# Generate plot outside of AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Generate the same plot outside AEDT.

solutions = maxwell_2d.post.get_solution_data("InputCurrent(PHA)", primary_sweep_variable="Time")
solutions.plot()

###############################################
# Close AEDT
# ~~~~~~~~~~
# Close AEDT.

maxwell_2d.release_desktop()
