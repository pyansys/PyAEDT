"""
Maxwell 3D: Transformer
-----------------------
This example shows how you can use PyAEDT to set core loss given a set
of Power-Volume [kw/m^3] curves at different frequencies.
"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

from pyaedt import downloads
from pyaedt import generate_unique_folder_name
from pyaedt import Maxwell3d
from pyaedt.generic.constants import unit_converter
from pyaedt.generic.general_methods import read_csv_pandas

#################################################################################
# Download .aedt file example
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Set local temporary folder to export the .aedt file to.

temp_folder = generate_unique_folder_name()
aedt_file = downloads.download_file("core_loss_transformer", "Ex2-PlanarTransformer_2023R2.aedtz", temp_folder)
freq_curve_csv_25kHz = downloads.download_file("core_loss_transformer", "mf3_25kHz.csv", temp_folder)
freq_curve_csv_100kHz = downloads.download_file("core_loss_transformer", "mf3_100kHz.csv", temp_folder)
freq_curve_csv_200kHz = downloads.download_file("core_loss_transformer", "mf3_200kHz.csv", temp_folder)
freq_curve_csv_400kHz = downloads.download_file("core_loss_transformer", "mf3_400kHz.csv", temp_folder)
freq_curve_csv_700kHz = downloads.download_file("core_loss_transformer", "mf3_700kHz.csv", temp_folder)
freq_curve_csv_1MHz = downloads.download_file("core_loss_transformer", "mf3_1MHz.csv", temp_folder)

data = read_csv_pandas(filename=freq_curve_csv_25kHz)
curves_csv_25kHz = list(zip(data[data.columns[0]],
                            data[data.columns[1]]))
data = read_csv_pandas(filename=freq_curve_csv_100kHz)
curves_csv_100kHz = list(zip(data[data.columns[0]],
                             data[data.columns[1]]))
data = read_csv_pandas(filename=freq_curve_csv_200kHz)
curves_csv_200kHz = list(zip(data[data.columns[0]],
                             data[data.columns[1]]))
data = read_csv_pandas(filename=freq_curve_csv_400kHz)
curves_csv_400kHz = list(zip(data[data.columns[0]],
                             data[data.columns[1]]))
data = read_csv_pandas(filename=freq_curve_csv_700kHz)
curves_csv_700kHz = list(zip(data[data.columns[0]],
                             data[data.columns[1]]))
data = read_csv_pandas(filename=freq_curve_csv_1MHz)
curves_csv_1MHz = list(zip(data[data.columns[0]],
                           data[data.columns[1]]))

###############################################################################
# Launch AEDT
# ~~~~~~~~~~~
# Launch AEDT 2023 R2 in graphical mode.

m3d = Maxwell3d(projectname=aedt_file,
                designname="02_3D eddycurrent_CmXY_for_thermal",
                specified_version="2023.2",
                new_desktop_session=True,
                non_graphical=False)

###############################################################################
# Set core loss at frequencies
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a new material, create a dictionary of Power-Volume [kw/m^3] points for a set of frequencies
# retrieved from datasheet provided by supplier and finally set Power-Ferrite core loss model.

mat = m3d.materials.add_material("newmat")
freq_25kHz = unit_converter(25, unit_system="Freq", input_units="kHz", output_units="Hz")
freq_100kHz = unit_converter(100, unit_system="Freq", input_units="kHz", output_units="Hz")
freq_200kHz = unit_converter(200, unit_system="Freq", input_units="kHz", output_units="Hz")
freq_400kHz = unit_converter(400, unit_system="Freq", input_units="kHz", output_units="Hz")
freq_700kHz = unit_converter(700, unit_system="Freq", input_units="kHz", output_units="Hz")
pv = {freq_25kHz: curves_csv_25kHz,
      freq_100kHz: curves_csv_100kHz,
      freq_200kHz: curves_csv_200kHz,
      freq_400kHz: curves_csv_400kHz,
      freq_700kHz: curves_csv_700kHz}
m3d.materials[mat.name].set_coreloss_at_frequency(points_list_at_freq=pv,
                                                  coefficient_setup="kw_per_cubic_meter",
                                                  core_loss_model_type="Power Ferrite")
coefficients = m3d.materials[mat.name].get_core_loss_coefficients(points_list_at_freq=pv,
                                                                  coefficient_setup="kw_per_cubic_meter")

###################################################################################
# Save project and close AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Save the project and close AEDT.

m3d.save_project()
m3d.release_desktop()
