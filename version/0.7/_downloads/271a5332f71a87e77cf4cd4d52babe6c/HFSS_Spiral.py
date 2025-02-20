"""
HFSS: spiral inductor
---------------------
This example shows how you can use PyAEDT to create a spiral inductor, solve it, and plot results.
"""

#############################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import pyaedt

project_name = pyaedt.generate_unique_project_name(project_name="spiral")

#############################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

#############################################################
# Launch HFSS
# ~~~~~~~~~~~
# Launch HFSS 2023 R2 in non-graphical mode and change the
# units to microns.

hfss = pyaedt.Hfss(specified_version="2023.2", non_graphical=non_graphical, designname="A1", new_desktop_session=True)
hfss.modeler.model_units = "um"
p = hfss.modeler

#############################################################
# Define variables
# ~~~~~~~~~~~~~~~~
# Define input variables. You can use the values that follow or edit
# them.

rin = 10
width = 2
spacing = 1
thickness = 1
Np = 8
Nr = 10
gap = 3
hfss["Tsub"] = "6" + hfss.modeler.model_units

#############################################################
# Standardize polyline
# ~~~~~~~~~~~~~~~~~~~~
# Standardize the polyline using the ``create_line`` method to fix
# the width, thickness, and material.

def create_line(pts):
    p.create_polyline(pts, xsection_type="Rectangle", xsection_width=width, xsection_height=thickness, matname="copper")


################################################################
# Create spiral inductor
# ~~~~~~~~~~~~~~~~~~~~~~
# Create the spiral inductor. This spiral inductor is not
# parametric, but you could parametrize it later.

ind = hfss.modeler.create_spiral(
    internal_radius=rin,
    width=width,
    spacing=spacing,
    turns=Nr,
    faces=Np,
    thickness=thickness,
    material="copper",
    name="Inductor1",
)


################################################################
# Center return path
# ~~~~~~~~~~~~~~~~~~
# Center the return path.

x0, y0, z0 = ind.points[0]
x1, y1, z1 = ind.points[-1]
create_line([(x0 - width / 2, y0, -gap), (abs(x1) + 5, y0, -gap)])
p.create_box([x0 - width / 2, y0 - width / 2, -gap - thickness / 2],
             [width, width, gap + thickness],
             matname="copper")

################################################################
# Create port 1
# ~~~~~~~~~~~~~
# Create port 1.

p.create_rectangle(csPlane=pyaedt.constants.PLANE.YZ,
                   position=[abs(x1) + 5, y0 - width / 2, -gap - thickness / 2],
                   dimension_list=[width, "Tsub+{}{}".format(gap, hfss.modeler.model_units)],
                   name="port1"
                   )
hfss.lumped_port(signal="port1", integration_line=pyaedt.constants.AXIS.Z)

################################################################
# Create port 2
# ~~~~~~~~~~~~~
# Create port 2.

create_line([(x1 + width / 2, y1, 0), (x1 - 5, y1, 0)])
p.create_rectangle(pyaedt.constants.PLANE.YZ, [x1 - 5, y1 - width / 2, -thickness / 2],
                   [width, "-Tsub"],
                   name="port2")
hfss.lumped_port(signal="port2", integration_line=pyaedt.constants.AXIS.Z)

################################################################
# Create silicon substrate and ground plane
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create the silicon substrate and the ground plane.

p.create_box([x1 - 20, x1 - 20, "-Tsub-{}{}/2".format(thickness, hfss.modeler.model_units)],
             [-2 * x1 + 40, -2 * x1 + 40, "Tsub"],
             matname="silicon")

p.create_box([x1 - 20, x1 - 20, "-Tsub-{}{}/2".format(thickness, hfss.modeler.model_units)],
             [-2 * x1 + 40, -2 * x1 + 40, -0.1],
             matname="PEC")

################################################################
# Assign airbox and radiation
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Assign the airbox and the radiation.

box = p.create_box(
    [x1 - 20, x1 - 20, "-Tsub-{}{}/2 - 0.1{}".format(thickness, hfss.modeler.model_units, hfss.modeler.model_units)],
    [-2 * x1 + 40, -2 * x1 + 40, 100],
    name="airbox",
    matname="air"
)

hfss.assign_radiation_boundary_to_objects("airbox")

################################################################
# Assign material override
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Assign a material override so that the validation check does
# not fail.

hfss.change_material_override()

###############################################################################
# Plot model
# ~~~~~~~~~~
# Plot the model.

hfss.plot(show=False, export_path=os.path.join(hfss.working_directory, "Image.jpg"), plot_air_objects=False)

################################################################
# Create setup
# ~~~~~~~~~~~~
# Create the setup and define a frequency sweep to solve the project.

setup1 = hfss.create_setup(setupname="setup1")
setup1.props["Frequency"] = "10GHz"
hfss.create_linear_count_sweep(setupname="setup1", unit="GHz", freqstart=1e-3, freqstop=50, num_of_freq_points=451,
                               sweep_type="Interpolating")
hfss.save_project()
hfss.analyze()

################################################################
# Get report data
# ~~~~~~~~~~~~~~~
# Get report data and use the following formulas to calculate
# the inductance and quality factor.

L_formula = "1e9*im(1/Y(1,1))/(2*pi*freq)"
Q_formula = "im(Y(1,1))/re(Y(1,1))"

################################################################
# Create output variable
# ~~~~~~~~~~~~~~~~~~~~~~
# Create output variable
hfss.create_output_variable("L", L_formula, solution="setup1 : LastAdaptive")

################################################################
# Plot calculated values in Matplotlib
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Plot the calculated values in Matplotlib.

data = hfss.post.get_solution_data([L_formula, Q_formula])
data.plot(curves=[L_formula, Q_formula], math_formula="re", xlabel="Freq", ylabel="L and Q")

################################################################
# Export results to csv file
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Export results to csv file
data.export_data_to_csv(os.path.join(hfss.toolkit_directory,"output.csv"))

################################################################
# Save project and close AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Save the project and close AEDT.

hfss.save_project(project_name)
hfss.release_desktop()
