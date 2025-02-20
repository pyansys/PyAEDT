"""
Multiphysics: HFSS-Icepak multiphysics analysis
------------------------------------------------
This example shows how you can create a project from scratch in HFSS and Icepak (linked to HFSS).
This includes creating a setup, solving it, and creating postprocessing outputs.

To provide the advanced postprocessing features needed for this example, the ``numpy``,
``matplotlib``, and ``pyvista`` packages must be installed on the machine.

This examples runs only on Windows using CPython.
"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import pyaedt
from pyaedt.generic.pdf import AnsysReport

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False
desktopVersion = "2023.2"

###############################################################################
# Open project
# ~~~~~~~~~~~~
# Open the project.

NewThread = True

project_file = pyaedt.generate_unique_project_name()

###############################################################################
# Launch AEDT and initialize HFSS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT and initialize HFSS. If there is an active HFSS design, the ``aedtapp``
# object is linked to it. Otherwise, a new design is created.

aedtapp = pyaedt.Hfss(projectname=project_file,
                      specified_version=desktopVersion,
                      non_graphical=non_graphical,
                      new_desktop_session=NewThread
                      )

###############################################################################
# Initialize variable settings
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Initialize variable settings. You can initialize a variable simply by creating
# it as a list object. If you enter the prefix ``$``, the variable is created for
# the project. Otherwise, the variable is created for the design.

aedtapp["$coax_dimension"] = "100mm"
udp = aedtapp.modeler.Position(0, 0, 0)
aedtapp["inner"] = "3mm"

###############################################################################
# Create coaxial and cylinders
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a coaxial and three cylinders. You can apply parameters
# directly using the :func:`pyaedt.modeler.Primitives3D.Primitives3D.create_cylinder`
# method. You can assign a material directly to the object creation action.
# Optionally, you can assign a material using the :func:`assign_material` method.

# TODO: How does this work when two truesurfaces are defined?
o1 = aedtapp.modeler.create_cylinder(cs_axis=aedtapp.PLANE.ZX, position=udp, radius="inner", height="$coax_dimension",
                                     numSides=0, name="inner")
o2 = aedtapp.modeler.create_cylinder(cs_axis=aedtapp.PLANE.ZX, position=udp, radius=8, height="$coax_dimension",
                                     numSides=0, matname="teflon_based")
o3 = aedtapp.modeler.create_cylinder(cs_axis=aedtapp.PLANE.ZX, position=udp, radius=10, height="$coax_dimension",
                                     numSides=0, name="outer")

###############################################################################
# Assign colors
# ~~~~~~~~~~~~~
# Assign colors to each primitive.

o1.color = (255, 0, 0)
o2.color = (0, 255, 0)
o3.color = (255, 0, 0)
o3.transparency = 0.8
aedtapp.modeler.fit_all()

###############################################################################
# Assign materials
# ~~~~~~~~~~~~~~~~
# Assign materials. You can assign materials either directly when creating the primitive,
# which was done for ``id2``, or after the object is created.

o1.material_name = "Copper"
o3.material_name = "Copper"

###############################################################################
# Perform modeler operations
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Perform modeler operations. You can subtract, add, and perform other operations
# using either the object ID or object name.

aedtapp.modeler.subtract(o3, o2, True)
aedtapp.modeler.subtract(o2, o1, True)

###############################################################################
# Perform mesh operations
# ~~~~~~~~~~~~~~~~~~~~~~~
# Perform mesh operations. Most mesh operations are available.
# After a mesh is created, you can access a mesh operation to
# edit or review parameter values.

aedtapp.mesh.assign_initial_mesh_from_slider(level=6)
aedtapp.mesh.assign_model_resolution(names=[o1.name, o3.name], defeature_length=None)
aedtapp.mesh.assign_length_mesh(names=o2.faces, isinside=False, maxlength=1, maxel=2000)

###############################################################################
# Create excitations
# ~~~~~~~~~~~~~~~~~~
# Create excitations. The ``create_wave_port_between_objects`` method automatically
# identifies the closest faces on a predefined direction and creates a sheet to cover
# the faces. It also assigns a port to this face. If ``add_pec_cap=True``, the method
# creates a PEC cap.

aedtapp.wave_port(signal="inner",
                  reference="outer",
                  integration_line=1,
                  create_port_sheet=True,
                  create_pec_cap=True,
                  name="P1")
aedtapp.wave_port(signal="inner",
                  reference="outer",
                  integration_line=4,
                  create_pec_cap=True,
                  create_port_sheet=True,
                  name="P2")

port_names = aedtapp.get_all_sources()
aedtapp.modeler.fit_all()

###############################################################################
# Create setup
# ~~~~~~~~~~~~
# Create a setup. A setup is created with default values. After its creation,
# you can change values and update the setup. The ``update`` method returns a Boolean
# value.

aedtapp.set_active_design(aedtapp.design_name)
setup = aedtapp.create_setup("MySetup")
setup.props["Frequency"] = "1GHz"
setup.props["BasisOrder"] = 2
setup.props["MaximumPasses"] = 1

###############################################################################
# Create sweep
# ~~~~~~~~~~~~
# Create a sweep. A sweep is created with default values.

sweepname = aedtapp.create_linear_count_sweep(setupname="MySetup", unit="GHz", freqstart=0.8, freqstop=1.2,
                                              num_of_freq_points=401, sweep_type="Interpolating")

################################################################################
# Create Icepak model
# ~~~~~~~~~~~~~~~~~~~
# Create an Icepak model. After an HFSS setup is ready, link this model to an Icepak
# project and run a coupled physics analysis. The :func:`FieldAnalysis3D.copy_solid_bodies_from`
# method imports a model from HFSS with all material settings.

ipkapp = pyaedt.Icepak()
ipkapp.copy_solid_bodies_from(aedtapp)

################################################################################
# Link sources to EM losses
# ~~~~~~~~~~~~~~~~~~~~~~~~~
# Link sources to the EM losses.

surfaceobj = ["inner", "outer"]
ipkapp.assign_em_losses(designname=aedtapp.design_name, setupname="MySetup", sweepname="LastAdaptive",
                        map_frequency="1GHz", surface_objects=surfaceobj, paramlist=["$coax_dimension", "inner"])

#################################################################################
# Edit gravity setting
# ~~~~~~~~~~~~~~~~~~~~
# Edit the gravity setting if necessary because it is important for a fluid analysis.

ipkapp.edit_design_settings(aedtapp.GRAVITY.ZNeg)

################################################################################
# Set up Icepak project
# ~~~~~~~~~~~~~~~~~~~~~
# Set up the Icepak project. When you create a setup, default settings are applied.
# When you need to change a property of the setup, you can use the ``props``
# command to pass the correct value to the property. The ``update`` function
# applies the settings to the setup. The setup creation process is identical
# for all tools.

setup_ipk = ipkapp.create_setup("SetupIPK")
setup_ipk.props["Convergence Criteria - Max Iterations"] = 3

################################################################################
# Edit or review mesh parameters
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Edit or review the mesh parameters. After a mesh is created, you can access
# a mesh operation to edit or review parameter values.

airbox = ipkapp.modeler.get_obj_id("Region")
ipkapp.modeler[airbox].display_wireframe = True
airfaces = ipkapp.modeler.get_object_faces(airbox)
ipkapp.assign_openings(airfaces)

################################################################################
# Close and open projects
# ~~~~~~~~~~~~~~~~~~~~~~~
# Close and open the projects to ensure that the HFSS - Icepak coupling works
# correctly in AEDT versions 2019 R3 through 2021 R1. Closing and opening projects
# can be helpful when performing operations on multiple projects.

aedtapp.save_project()
aedtapp.close_project(aedtapp.project_name)
aedtapp = pyaedt.Hfss(project_file)
ipkapp = pyaedt.Icepak()
ipkapp.solution_type = ipkapp.SOLUTIONS.Icepak.SteadyTemperatureAndFlow
ipkapp.modeler.fit_all()

################################################################################
# Solve Icepak project
# ~~~~~~~~~~~~~~~~~~~~
# Solve the Icepak project and the HFSS sweep.

setup1 = ipkapp.analyze_setup("SetupIPK")
aedtapp.save_project()
aedtapp.modeler.fit_all()
aedtapp.analyze_setup("MySetup")

################################################################################
# Generate field plots and export
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Generate field plots on the HFSS project and export them as images.

cutlist = [pyaedt.constants.GLOBALCS.XY, pyaedt.constants.GLOBALCS.ZX, pyaedt.constants.GLOBALCS.YZ]
vollist = [o2.name]
setup_name = "MySetup : LastAdaptive"
quantity_name = "ComplexMag_E"
quantity_name2 = "ComplexMag_H"
intrinsic = {"Freq": "1GHz", "Phase": "0deg"}
surflist = aedtapp.modeler.get_object_faces("outer")
plot1 = aedtapp.post.create_fieldplot_surface(surflist, quantity_name2, setup_name, intrinsic)

results_folder = os.path.join(aedtapp.working_directory, "Coaxial_Results_NG")
if not os.path.exists(results_folder):
    os.mkdir(results_folder)

aedtapp.post.plot_field_from_fieldplot(
    plot1.name,
    project_path=results_folder,
    meshplot=False,
    imageformat="jpg",
    view="isometric",
    show=False,
    plot_cad_objs=False,
    log_scale = False,
)

################################################################################
# Generate animation from field plots
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Generate an animation from field plots using PyVista.

import time

start = time.time()
cutlist = ["Global:XY"]
phases = [str(i * 5) + "deg" for i in range(18)]

animated = aedtapp.post.plot_animated_field(
    quantity="Mag_E",
    object_list=cutlist,
    plot_type="CutPlane",
    setup_name=aedtapp.nominal_adaptive,
    intrinsics={"Freq": "1GHz", "Phase": "0deg"},
    export_path=results_folder,
    variation_variable="Phase",
    variation_list=phases,
    show=False,
    export_gif=False,
    log_scale=True,
)
animated.gif_file = os.path.join(aedtapp.working_directory, "animate.gif")
animated.camera_position = [0, 0, 300]
animated.focal_point = [0, 0, 0]
# Set off_screen to False to visualize the animation.
# animated.off_screen = False
animated.animate()

endtime = time.time() - start
print("Total Time", endtime)

################################################################################
# Create Icepak plots and export
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create Icepak plots and export them as images using the same functions that
# were used early. Only the quantity is different.

quantity_name = "Temperature"
setup_name = ipkapp.existing_analysis_sweeps[0]
intrinsic = ""
surflist = ipkapp.modeler.get_object_faces("inner") + ipkapp.modeler.get_object_faces("outer")
plot5 = ipkapp.post.create_fieldplot_surface(surflist, "SurfTemperature")

aedtapp.save_project()

################################################################################
# Generate plots outside of AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Generate plots outside of AEDT using Matplotlib and NumPy.

trace_names = aedtapp.get_traces_for_plot(category="S")
cxt = ["Domain:=", "Sweep"]
families = ["Freq:=", ["All"]]
my_data = aedtapp.post.get_solution_data(expressions=trace_names)
my_data.plot(trace_names, "db20",
             xlabel="Frequency (Ghz)",
             ylabel="SParameters(dB)",
             title="Scattering Chart",
             snapshot_path=os.path.join(results_folder, "Touchstone_from_matplotlib.jpg"))

################################################################################
# Generate pdf report
# ~~~~~~~~~~~~~~~~~~~
# Generate a pdf report with output of simultion.
report = AnsysReport(project_name=aedtapp.project_name, design_name=aedtapp.design_name,version=desktopVersion)
report.create()


report.add_section()
report.add_chapter("Hfss Results")
report.add_sub_chapter("Field Plot")
report.add_text("This section contains Field plots of Hfss Coaxial.")
report.add_image(os.path.join(results_folder, plot1.name+".jpg"), "Coaxial Cable")
report.add_page_break()
report.add_sub_chapter("S Parameters")
report.add_chart(my_data.intrinsics["Freq"], my_data.data_db20(), "Freq", trace_names[0], "S-Parameters")
report.add_image(os.path.join(results_folder, "Touchstone_from_matplotlib.jpg"), "Touchstone from Matplotlib")
report.add_section()
report.add_chapter("Icepak Results")
report.add_sub_chapter("Temperature Plot")
report.add_text("This section contains Multiphysics temperature plot.")

#report.add_image(os.path.join(results_folder, plot5.name+".jpg"), "Coaxial Cable Temperatures")
report.add_toc()
report.save_pdf(results_folder, "AEDT_Results.pdf")



################################################################################
# Close project and release AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Close the project and release AEDT.

aedtapp.release_desktop()
