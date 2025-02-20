"""
Multiphysics: Maxwell 3D - Icepak electrothermal analysis
---------------------------------------------------------
This example uses PyAEDT to set up a simple Maxwell design consisting of a coil and a ferrite core.
Coil current is set to 100A, and coil resistance and ohmic loss are analyzed.
Ohmic loss is mapped to Icepak, and a thermal analysis is performed. Icepak calculates a temperature distribution,
and it is mapped back to Maxwell (2-way coupling). Coil resistance and ohmic loss are analyzed again in Maxwell.
Results are printed in AEDT Message Manager.
"""
###########################################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import pyaedt
from pyaedt.generic.constants import AXIS

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

###########################################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode.
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

###########################################################################################
# Launch AEDT and Maxwell 3D
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT and Maxwell 3D. The following code sets up the project and design names, the solver, and
# the version. It also creates an instance of the ``Maxwell3d`` class named ``m3d``.

project_name = "Maxwell-Icepak-2way-Coupling"
maxwell_design_name = "1 Maxwell"
icepak_design_name = "2 Icepak"

m3d = pyaedt.Maxwell3d(
    projectname=project_name,
    designname=maxwell_design_name,
    solution_type="EddyCurrent",
    specified_version=aedt_version,
    non_graphical=non_graphical,
)

###############################################################################
# Create geometry in Maxwell
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create the coil, coil terminal, core, and region.

coil = m3d.modeler.create_rectangle(
    orientation="XZ", origin=[70, 0, -11], sizes=[11, 110], name="Coil"
)

coil.sweep_around_axis(axis=AXIS.Z)

coil_terminal = m3d.modeler.create_rectangle(
    orientation="XZ", origin=[70, 0, -11], sizes=[11, 110], name="Coil_terminal"
)

core = m3d.modeler.create_rectangle(
    orientation="XZ", origin=[45, 0, -18], sizes=[7, 160], name="Core"
)
core.sweep_around_axis(axis=AXIS.Z)

# Magnetic flux is not concentrated by the core in +z-direction. Therefore, more padding is needed in that direction.
region = m3d.modeler.create_region(pad_percent=[20, 20, 500, 20, 20, 100])

###############################################################################
# Assign materials
# ~~~~~~~~~~~~~~~~
# Create a material: Copper AWG40 Litz wire, strand diameter = 0.08mm, 24 parallel strands.
# Assign materials: Assign Coil to AWG40 copper, core to ferrite, and region to vacuum.

no_strands = 24
strand_diameter = 0.08

cu_litz = m3d.materials.duplicate_material("copper", "copper_litz")
cu_litz.stacking_type = "Litz Wire"
cu_litz.wire_diameter = str(strand_diameter) + "mm"
cu_litz.wire_type = "Round"
cu_litz.strand_number = no_strands

m3d.assign_material(region.name, "vacuum")
m3d.assign_material(coil.name, "copper_litz")
m3d.assign_material(core.name, "ferrite")

###############################################################################
# Assign excitation
# ~~~~~~~~~~~~~~~~~
# Assign coil current, coil consists of 20 turns, total current 10A.
# Note that each coil turn consists of 24 parallel Litz strands, see above.

no_turns = 20
coil_current = 10
m3d.assign_coil(["Coil_terminal"], conductors_number=no_turns, name="Coil_terminal")
m3d.assign_winding(is_solid=False, current=coil_current, name="Winding1")

m3d.add_winding_coils(assignment="Winding1", coils=["Coil_terminal"])

###############################################################################
# Assign mesh operations
# ~~~~~~~~~~~~~~~~~~~~~~
# Mesh operations are not necessary in eddy current solver because of auto-adaptive meshing.
# However, with appropriate mesh operations, less adaptive passes are needed.

m3d.mesh.assign_length_mesh(["Core"], maximum_length=15, maximum_elements=None, name="Inside_Core")
m3d.mesh.assign_length_mesh(["Coil"], maximum_length=30, maximum_elements=None, name="Inside_Coil")

###############################################################################
# Set conductivity temperature coefficient
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Set conductivity as a function of temperature. Resistivity increases by 0.393% per K.

cu_resistivity_temp_coefficient = 0.00393
cu_litz.conductivity.add_thermal_modifier_free_form("1.0/(1.0+{}*(Temp-20))".format(cu_resistivity_temp_coefficient))

###############################################################################
# Set object temperature and enable feedback
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Set the temperature of the objects to default temperature (22deg C)
# and enable temperature feedback for two-way coupling.

m3d.modeler.set_objects_temperature(["Coil"])

###############################################################################
# Assign matrix
# ~~~~~~~~~~~~~
# Resistance and inductance calculation.

m3d.assign_matrix(["Winding1"], matrix_name="Matrix1")

###############################################################################
# Create and analyze simulation setup
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Simulation frequency 150kHz.

setup = m3d.create_setup(name="Setup1")
setup.props["Frequency"] = "150kHz"
m3d.analyze_setup("Setup1")

###############################################################################
# Postprocessing
# ~~~~~~~~~~~~~~
# Calculate analytical DC resistance and compare it with the simulated coil resistance,
# print them in the message manager, as well as ohmic loss in coil before temperature feedback.

report = m3d.post.create_report(expressions="Matrix1.R(Winding1,Winding1)")
solution = report.get_solution_data()
resistance = solution.data_magnitude()[0]

report_loss = m3d.post.create_report(expressions="StrandedLossAC")
solution_loss = report_loss.get_solution_data()
em_loss = solution_loss.data_magnitude()[0]

# Analytical calculation of the DC resistance of the coil
cu_cond = float(cu_litz.conductivity.value)
# average radius of a coil turn = 0.125m
l_conductor = no_turns*2*0.125*3.1415
# R = resistivity * length / area / no_strand
r_analytical_DC = (1.0 / cu_cond) * l_conductor / (3.1415 * (strand_diameter / 1000 / 2) ** 2) / no_strands

# Print results in the Message Manager
m3d.logger.info("*******Coil analytical DC resistance =  {:.2f}Ohm".format(r_analytical_DC))
m3d.logger.info("*******Coil resistance at 150kHz BEFORE temperature feedback =  {:.2f}Ohm".format(resistance))
m3d.logger.info("*******Ohmic loss in coil BEFORE temperature feedback =  {:.2f}W".format(em_loss / 1000))

###############################################################################
# Icepak design
# ~~~~~~~~~~~~~
# Insert Icepak design, copy solid objects from Maxwell, and modify region dimensions.

ipk = pyaedt.Icepak(designname=icepak_design_name)
ipk.copy_solid_bodies_from(m3d, no_pec=False)

# Set domain dimensions suitable for natural convection using the diameter of the coil
ipk.modeler["Region"].delete()
coil_dim = coil.bounding_dimension[0]
ipk.modeler.create_region(0, False)
ipk.modeler.edit_region_dimensions([coil_dim / 2, coil_dim / 2, coil_dim / 2, coil_dim / 2, coil_dim * 2, coil_dim])

###############################################################################
# Map coil losses
# ~~~~~~~~~~~~~~~
# Map ohmic losses from Maxwell to the Icepak design.

ipk.assign_em_losses(design="1 Maxwell", setup=m3d.setups[0].name, sweep="LastAdaptive", assignment=["Coil"])

###############################################################################
# Boundary conditions
# ~~~~~~~~~~~~~~~~~~~
# Assign opening.

faces = ipk.modeler["Region"].faces
face_names = [face.id for face in faces]
ipk.assign_free_opening(face_names, boundary_name="Opening1")

###############################################################################
# Assign monitor
# ~~~~~~~~~~~~~~
# Temperature monitor on the coil surface

temp_monitor = ipk.assign_point_monitor([70, 0, 0], monitor_name="PointMonitor1")

###############################################################################
# Icepak solution setup
# ~~~~~~~~~~~~~~~~~~~~~

solution_setup = ipk.create_setup()
solution_setup.props["Convergence Criteria - Max Iterations"] = 50
solution_setup.props["Flow Regime"] = "Turbulent"
solution_setup.props["Turbulent Model Eqn"] = "ZeroEquation"
solution_setup.props["Radiation Model"] = "Discrete Ordinates Model"
solution_setup.props["Include Flow"] = True
solution_setup.props["Include Gravity"] = True
solution_setup.props["Solution Initialization - Z Velocity"] = "0.0005m_per_sec"
solution_setup.props["Convergence Criteria - Flow"] = 0.0005
solution_setup.props["Flow Iteration Per Radiation Iteration"] = "5"


###############################################################################
# Add 2-way coupling and solve the project
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Enable mapping temperature distribution back to Maxwell.
# Default number Maxwell <--> Icepak iterations is 2,
# but for increased accuracy it can be increased (number_of_iterations).

ipk.assign_2way_coupling()
ipk.analyze_setup(name=solution_setup.name)

###############################################################################
# Postprocessing
# ~~~~~~~~~~~~~~
# Plot temperature on the object surfaces.

surface_list = []
for name in ["Coil", "Core"]:
    surface_list.extend(ipk.modeler.get_object_faces(name))

surf_temperature = ipk.post.create_fieldplot_surface(surface_list, quantity="SurfTemperature",
                                                     plot_name="Surface Temperature")

velocity_cutplane = ipk.post.create_fieldplot_cutplane(assignment=["Global:XZ"], quantity="Velocity Vectors",
                                                       plot_name="Velocity Vectors")

surf_temperature.export_image()
velocity_cutplane.export_image(orientation="right")

report_temp = ipk.post.create_report(expressions="PointMonitor1.Temperature", primary_sweep_variable="X")
solution_temp = report_temp.get_solution_data()
temp = solution_temp.data_magnitude()[0]
m3d.logger.info("*******Coil temperature =  {:.2f}deg C".format(temp))

###############################################################################
# Get new resistance from Maxwell
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Temperature of the coil increases, and consequently also coil resistance increases.

report_new = m3d.post.create_report(expressions="Matrix1.R(Winding1,Winding1)")
solution_new = report_new.get_solution_data()
resistance_new = solution_new.data_magnitude()[0]
resistance_increase = (resistance_new - resistance)/resistance * 100

report_loss_new = m3d.post.create_report(expressions="StrandedLossAC")
solution_loss_new = report_loss_new.get_solution_data()
em_loss_new = solution_loss_new.data_magnitude()[0]

m3d.logger.info("*******Coil resistance at 150kHz AFTER temperature feedback =  {:.2f}Ohm".format(resistance_new))
m3d.logger.info("*******Coil resistance increased by {:.2f}%".format(resistance_increase))
m3d.logger.info("*******Ohmic loss in coil AFTER temperature feedback =  {:.2f}W".format(em_loss_new/1000))

##################################################################################
# Release desktop
# ~~~~~~~~~~~~~~~

ipk.release_desktop(True, True)
