"""
Maxwell 2D: resistance calculation
----------------------------------
This example uses PyAEDT to set up a resistance calculation
and solve it using the Maxwell 2D DCConduction solver.
Keywords: DXF import, material sweep, expression cache
"""
import os.path

import pyaedt

from pyaedt.generic.pdf import AnsysReport

##################################################################################
# Launch AEDT and Maxwell 2D
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT and Maxwell 2D after first setting up the project and design names,
# the solver, and the version. The following code also creates an instance of the
# ``Maxwell2d`` class named ``m2d``.

m2d = pyaedt.Maxwell2d(
    specified_version="2023.2",
    new_desktop_session=True,
    close_on_exit=True,
    solution_type="DCConduction",
    projectname="M2D_DC_Conduction",
    designname="Ansys_resistor"
)

##########################################################
# Create results folder
# ~~~~~~~~~~~~~~~~~~~~
# Create results folder.

results_folder = os.path.join(m2d.working_directory, "M2D_DC_Conduction")
if not os.path.exists(results_folder):
    os.mkdir(results_folder)

##################################################################################
# Import geometry as a DXF file
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# You can test importing a DXF or a Parasolid file by commenting/uncommenting
# the following lines.
# Importing DXF files only works in graphical mode.

# DXFPath = pyaedt.downloads.download_file("dxf", "Ansys_logo_2D.dxf")
# dxf_layers = m2d.get_dxf_layers(DXFPath)
# m2d.import_dxf(DXFPath, dxf_layers, scale=1E-05)

ParasolidPath = pyaedt.downloads.download_file("x_t", "Ansys_logo_2D.x_t")
m2d.modeler.import_3d_cad(ParasolidPath)

##################################################################################
# Define variables
# ~~~~~~~~~~~~~~~~
# Define conductor thickness in z-direction, material array with 4 materials,
# and MaterialIndex referring to the material array

m2d["MaterialThickness"] = "5mm"
m2d["ConductorMaterial"] = "[\"Copper\", \"Aluminum\", \"silver\", \"gold\"]"
MaterialIndex = 0
m2d["MaterialIndex"] = str(MaterialIndex)
no_materials = 4


##################################################################################
# Assign materials
# ~~~~~~~~~~~~~~~~
# Voltage ports will be defined as perfect electric conductor (pec), conductor
# gets the material defined by the 0th entry of the material array

m2d.assign_material(["ANSYS_LOGO_2D_1", "ANSYS_LOGO_2D_2"], "pec")
m2d.modeler["ANSYS_LOGO_2D_3"].material_name = "ConductorMaterial[MaterialIndex]"

##################################################################################
# Assign voltages
# ~~~~~~~~~~~~~~~
# 1V and 0V

m2d.assign_voltage(["ANSYS_LOGO_2D_1"], amplitude=1, name="1V")
m2d.assign_voltage(["ANSYS_LOGO_2D_2"], amplitude=0, name="0V")

##################################################################################
# Setup conductance calculation
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 1V is the source, 0V ground

m2d.assign_matrix(sources=['1V'], group_sources=['0V'], matrix_name="Matrix1")

##################################################################################
# Assign mesh operation
# ~~~~~~~~~~~~~~~~~~~~~
# 3mm on the conductor

m2d.mesh.assign_length_mesh(["ANSYS_LOGO_2D_3"], meshop_name="conductor", maxlength=3, maxel=None)

##################################################################################
# Create simulation setup and enable expression cache
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create simulation setup with minimum 4 adaptive passes to ensure convergence.
# Enable expression cache to observe the convergence.

setup1 = m2d.create_setup(setupname="Setup1", MinimumPasses=4)
setup1.enable_expression_cache( # doesn't work?
    report_type="DCConduction",
    expressions="1/Matrix1.G(1V,1V)/MaterialThickness",
    isconvergence=True,
    conv_criteria=1,
    use_cache_for_freq=False)
setup1.analyze()

##################################################################################
# Create parametric sweep
# ~~~~~~~~~~~~~~~~~~~~~~~
# Create parametric sweep to sweep all the entries in the material array.
# Save fields and mesh and use the mesh for all the materials.

param_sweep = m2d.parametrics.add(
    "MaterialIndex", 0, no_materials-1, 1, "LinearStep",
    parametricname="MaterialSweep")
param_sweep["SaveFields"] = True
param_sweep["CopyMesh"] = True
param_sweep["SolveWithCopiedMeshOnly"] = True
param_sweep.analyze()

##################################################################################
# Create resistance report
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Create R. vs. material report

variations = {"MaterialIndex": ["All"], "MaterialThickness": ["Nominal"]}
report = m2d.post.create_report(
    expressions="1/Matrix1.G(1V,1V)/MaterialThickness",
    primary_sweep_variable="MaterialIndex",
    report_category="DCConduction",
    plot_type="Data Table",
    variations=variations,
    plotname="Resistance vs. Material",
)
d = report.get_solution_data()
resistence = d.data_magnitude()
material_index = d.primary_sweep_values
d.primary_sweep = "MaterialIndex"
d.plot(snapshot_path=os.path.join(results_folder, "M2D_DCConduction.jpg"))

material_index_vs_resistance = [["Material", "Resistance"]]
colors = [[(255, 255, 255), (0, 255, 0)]]
for i in range(len(d.primary_sweep_values)):
    material_index_vs_resistance.append([str(d.primary_sweep_values[i]), str(resistence[i])])
    colors.append([None, None])

##################################################################################
# Field overlay
# ~~~~~~~~~~~~~
# Plot electric field and current density on the conductor surface

conductor_surface = m2d.modeler["ANSYS_LOGO_2D_3"].faces
plot1 = m2d.post.create_fieldplot_surface(conductor_surface, "Mag_E", plot_name="Electric Field")
plot2 = m2d.post.create_fieldplot_surface(conductor_surface, "Mag_J", plot_name="Current Density")

##################################################################################
# Field overlay
# ~~~~~~~~~~~~~
# Plot electric field using pyvista and saving to an image

py_vista_plot = m2d.post.plot_field("Mag_E", conductor_surface, plot_cad_objs=False, show=False)
py_vista_plot.isometric_view = False
py_vista_plot.camera_position = [0, 0, 7]
py_vista_plot.focal_point = [0, 0, 0]
py_vista_plot.roll_angle = 0
py_vista_plot.elevation_angle = 0
py_vista_plot.azimuth_angle = 0
py_vista_plot.plot(os.path.join(results_folder, "mag_E.jpg"))

##################################################################################
# Field animation
# ~~~~~~~~~~~~~~~
# Plot current density vs the Material index.

animated = m2d.post.plot_animated_field(
    quantity="Mag_J",
    object_list=conductor_surface,
    export_path=results_folder,
    variation_variable="MaterialIndex",
    variation_list=[0,1,2,3],
    show=False,
    export_gif=False,
    log_scale=True,
)
animated.isometric_view = False
animated.camera_position = [0, 0, 7]
animated.focal_point = [0, 0, 0]
animated.roll_angle = 0
animated.elevation_angle = 0
animated.azimuth_angle = 0
animated.animate()

################################################################################
# Export model picture
# ~~~~~~~~~~~~~~~~~~~~
# Export model picture.

model_picture = m2d.post.export_model_picture()

################################################################################
# Generate PDF report
# ~~~~~~~~~~~~~~~~~~~
# Generate a PDF report with output of simulation.

pdf_report = AnsysReport(project_name=m2d.project_name, design_name=m2d.design_name, version="2023.2")
pdf_report.report_specs.font = "times"
pdf_report.report_specs.text_font_size = 10
pdf_report.project_name = m2d.project_name
pdf_report.create()
pdf_report.add_project_info(m2d)
pdf_report.add_chapter("Model Picture")
pdf_report.add_text("This section contains the model picture")
pdf_report.add_image(model_picture, "Model Picture", width=80, height=60)
pdf_report.add_chapter("Field overlay")
pdf_report.add_sub_chapter("Plots")
pdf_report.add_text("This section contains the fields overlay.")
pdf_report.add_image(os.path.join(results_folder, "mag_E.jpg"), "Mag E", width=120, height=80)
pdf_report.add_page_break()
pdf_report.add_section()
pdf_report.add_chapter("Results")
pdf_report.add_sub_chapter("Resistance vs. Material")
pdf_report.add_text("This section contains resistance vs material data.")
# Aspect ratio is automatically calculated if only width is provided
pdf_report.add_image(os.path.join(results_folder, "M2D_DCConduction.jpg"), width=130)
pdf_report.add_sub_chapter("Resistance data table")
pdf_report.add_text("This section contains Resistance data.")
pdf_report.add_table("Resistance Data", content=material_index_vs_resistance, formatting=colors, col_widths=[75, 100])
pdf_report.add_toc()
pdf_report.save_pdf(results_folder, "AEDT_Results.pdf")

##################################################################################
# Release desktop
# ~~~~~~~~~~~~~~~
m2d.release_desktop()
