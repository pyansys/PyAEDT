"""
Multiphysics: HFSS-Mechanical MRI analysis
---------------------------------------------------
The goal of this workshop is to use a coil tuned to 63.8 MHz to determine the temperature
rise in a gel phantom near an implant given a background SAR of 1 W/kg.

Steps to follow
Step 1: Simulate coil loaded by empty phantom:
Scale input to coil ports to produce desired background SAR of 1 W/kg at location that will later contain the implant.
Step 2: Simulate coil loaded by phantom containing implant in proper location:
View SAR in tissue surrounding implant.
Step 3: Thermal simulation:
Link HFSS to transient thermal solver to find temperature rise in tissue near implant vs. time.
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.
import os.path

from pyaedt import Hfss, Mechanical, Icepak, downloads

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. `
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

###############################################################################
# Project load
# ~~~~~~~~~~~~
# Open the ANSYS Electronics Desktop 2018.2
# Open project background_SAR.aedt
# Project contains phantom and airbox
# Phantom consists of two objects: phantom and implant_box
# Separate objects are used to selectively assign mesh operations
# Material properties defined in  this project already contain #electrical and thermal properties.
project_path = downloads.download_file(directory="mri")
hfss = Hfss(os.path.join(project_path, "background_SAR.aedt"), specified_version="2023.2", non_graphical=non_graphical,
            new_desktop_session=True)
###############################################################################
# Insert 3D component
# ~~~~~~~~~~~~~~~~~~~
# The MRI Coil is saved as a separate 3D Component
# ‒ 3D Components store geometry (including parameters),
# material properties, boundary conditions, mesh assignments,
# and excitations
# ‒ 3D Components make it easy to reuse and share parts of a simulation

hfss.modeler.insert_3d_component(os.path.join(project_path, "coil.a3dcomp"))

###############################################################################
# Expression Chache
# ~~~~~~~~~~~~~~~~~
#  On the expression cache tab, define additional convergence criteria for self impedance of the four coil
# ports
# ‒ Set each of these convergence criteria to 2.5 ohm
# For this demo number of passes is limited to 2 to reduce simulation time.

im_traces = hfss.get_traces_for_plot(get_mutual_terms=False, category="im(Z", first_element_filter="Coil1_p*")

hfss.setups[0].enable_expression_cache(
    report_type="Modal Solution Data",
    expressions=im_traces,
    isconvergence=True,
    isrelativeconvergence=False,
    conv_criteria=2.5,
    use_cache_for_freq=False)
hfss.setups[0].props["MaximumPasses"] = 2
im_traces

###############################################################################
# Edit Sources
# ~~~~~~~~~~~~
# The 3D Component of the MRI Coil contains all the ports,
# but the sources for these ports are not yet defined.
# Browse to and select sources.csv.
# These sources were determined by tuning this coil at 63.8 MHz.
# Notice the “*input_scale” multiplier to allow quick adjustment of the coil excitation power.

hfss.edit_sources_from_file(os.path.join(project_path, "sources.csv"))

###############################################################################
# Run Simulation
# ~~~~~~~~~~~~~~
# Save and analyze the project.

hfss.save_project(os.path.join(project_path, "solved.aedt"))
hfss.analyze(num_cores=6)

###############################################################################
# Plot SAR on Cut Plane in Phantom
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Ensure that the SAR averaging method is set to Gridless
# Plot averagedSAR on GlobalYZ plane
# Draw Point1 at origin of the implant coordinate system

hfss.sar_setup(-1, Average_SAR_method=1, TissueMass=1, MaterialDensity=1, )
hfss.post.create_fieldplot_cutplane("implant:YZ", "Average_SAR", filter_objects=["implant_box"])

hfss.modeler.set_working_coordinate_system("implant")
hfss.modeler.create_point([0, 0, 0], name="Point1")

###############################################################################
# Adjust Input Power to MRI Coil
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# The goal is to adjust the MRI coil’s input power, so that the averageSAR at Point1 is 1 W/kg
# Note that SAR and input power are linearly related
# To determine required input, calculate
# input_scale = 1/AverageSAR at Point1


sol_data = hfss.post.get_solution_data("Average_SAR", primary_sweep_variable="Freq", context="Point1",
                                       report_category="Fields")
sol_data.data_real()

hfss["input_scale"] = 1 / sol_data.data_real()[0]

###############################################################################
# Phantom with Implant
# ~~~~~~~~~~~~~~~~~~~~
# Import implant geometry.
# Subtract rod from implant_box.
# Assign titanium to the imported object rod.
# Analyze the project.

hfss.modeler.import_3d_cad(os.path.join(project_path, "implant_rod.sat"))

hfss.modeler["implant_box"].subtract("rod", keep_originals=True)
hfss.modeler["rod"].material_name = "titanium"
hfss.analyze(num_cores=6)
hfss.save_project()

###############################################################################
# Thermal Simulation
# ~~~~~~~~~~~~~~~~~~
# Initialize a new Mechanical Transient Thermal analysis.
# Mechanical Transient Thermal is available in AEDT from 2023 R2 as a Beta feature.

mech = Mechanical(solution_type="Transient Thermal", specified_version="2023.2")

###############################################################################
# Copy geometries
# ~~~~~~~~~~~~~~~
# Copy bodies from the HFSS project. 3D Component will not be copied.

mech.copy_solid_bodies_from(hfss)

################################################################################
# Link sources to EM losses
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Link sources to the EM losses.
# Assign external convection.

exc = mech.assign_em_losses(
    designname=hfss.design_name,
    setupname=hfss.setups[0].name,
    sweepname="LastAdaptive",
    map_frequency=hfss.setups[0].props["Frequency"],
    surface_objects=mech.get_all_conductors_names(),
)
mech.assign_uniform_convection(mech.modeler["Region"].faces, convection_value=1)

################################################################################
# Create Setup
# ~~~~~~~~~~~~
# Create a new setup and edit properties.
# Simuation will be for 60 seconds.

setup = mech.create_setup()
# setup.add_mesh_link("backgroundSAR")
# mech.create_dataset1d_design("PowerMap", [0, 239, 240, 360], [1, 1, 0, 0])
# exc.props["LossMultiplier"] = "pwl(PowerMap,Time)"

mech.modeler.set_working_coordinate_system("implant")
mech.modeler.create_point([0, 0, 0], name="Point1")
setup.props["Stop Time"] = 60
setup.props["Time Step"] = "10s"
setup.props["SaveFieldsType"] = "Every N Steps"
setup.props["N Steps"] = "2"

###############################################################################
# Analyze Mechanical
# ~~~~~~~~~~~~~~~~~~
# Analyze the project.

mech.analyze(num_cores=6)

###############################################################################
# Plot Fields
# ~~~~~~~~~~~
# Plot Temperature on cut plane.
# Plot Temperature on point.


mech.post.create_fieldplot_cutplane("implant:YZ", "Temperature", filter_objects=["implant_box"],
                                    intrinsincDict={"Time": "10s"})
mech.save_project()

data = mech.post.get_solution_data("Temperature", primary_sweep_variable="Time", context="Point1",
                                   report_category="Fields")
data.plot()

###############################################################################
# Thermal Simulation
# ~~~~~~~~~~~~~~~~~~
# Initialize a new Icepak Transient Thermal analysis.

ipk = Icepak(solution_type="Transient", specified_version="2023.2")
ipk.design_solutions.problem_type = "TemperatureOnly"

###############################################################################
# Copy geometries
# ~~~~~~~~~~~~~~~
# Copy bodies from the HFSS project. 3D Component will not be copied.

ipk.modeler.delete("Region")
ipk.copy_solid_bodies_from(hfss)

################################################################################
# Link sources to EM losses
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Link sources to the EM losses.
# Assign external convection.

exc = ipk.assign_em_losses(
    designname=hfss.design_name,
    setupname=hfss.setups[0].name,
    sweepname="LastAdaptive",
    map_frequency=hfss.setups[0].props["Frequency"],
    surface_objects=ipk.get_all_conductors_names(),
)

################################################################################
# Create Setup
# ~~~~~~~~~~~~
# Create a new setup and edit properties.
# Simuation will be for 60 seconds.

setup = ipk.create_setup()

setup.props["Stop Time"] = 60
setup.props["N Steps"] = 2
setup.props["Time Step"] = 5
setup.props['Convergence Criteria - Energy'] = 1e-12

################################################################################
# Mesh Region
# ~~~~~~~~~~~
# Create a new mesh region and change accuracy level to 4.


bound = ipk.modeler["implant_box"].bounding_box
mesh_box = ipk.modeler.create_box(bound[:3], [bound[3] - bound[0], bound[4] - bound[1], bound[5] - bound[2]])
mesh_box.model = False
mesh_region = ipk.mesh.assign_mesh_region([mesh_box.name])
mesh_region.UserSpecifiedSettings = False
mesh_region.Level = 4
mesh_region.update()

################################################################################
# Point Monitor
# ~~~~~~~~~~~~~
# Create a new point monitor.

ipk.modeler.set_working_coordinate_system("implant")
ipk.monitor.assign_point_monitor([0, 0, 0], monitor_name="Point1")
ipk.assign_openings(ipk.modeler["Region"].top_face_z)

###############################################################################
# Analyze and plot fields
# ~~~~~~~~~~~~~~~~~~~~~~~
# Analyze the project.
# Plot Temperature on cut plane.
# Plot Temperature on monitor point.

ipk.analyze(num_cores=6)
ipk.post.create_fieldplot_cutplane("implant:YZ", "Temperature", filter_objects=["implant_box"],
                                   intrinsincDict={"Time": "0s"})
ipk.save_project()

data = ipk.post.get_solution_data("Point1.Temperature", primary_sweep_variable="Time", report_category="Monitor")
data.plot()

ipk.release_desktop(False)
