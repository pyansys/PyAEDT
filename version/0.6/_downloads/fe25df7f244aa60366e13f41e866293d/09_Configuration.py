"""
EDB: Pin to Pin project
-----------------------
This example shows how you can create a project using a BOM file and configuration files.
run anlasyis and get results.

"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Peform required imports. Importing the ``Hfss3dlayout`` object initializes it
# on version 2023 R2.

import os
import pyaedt

##########################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. The default is ``True``.

non_graphical = True

###############################################################################
# Download file
# ~~~~~~~~~~~~~
# Download the AEDB file and copy it in the temporary folder.


project_path = pyaedt.generate_unique_folder_name()
target_aedb = pyaedt.downloads.download_file('edb/ANSYS-HSD_V1.aedb', destination=project_path)
print("Project folder will be", target_aedb)

###############################################################################
# Launch EDB
# ~~~~~~~~~~
# Launch the :class:`pyaedt.Edb` class, using EDB 2023 R2 and SI units.

edbapp = pyaedt.Edb(target_aedb, edbversion="2023.2")
###############################################################################
# Import Definitions
# ~~~~~~~~~~~~~~~~~~
# A definitions file is a json containing, for each part name the model associated.
# Model can be RLC, Sparameter or Spice.
# Once imported the definition is applied to the board.
# In this example the json file is stored for convenience in aedb folder and has the following format:
# {
#     "SParameterModel": {
#         "GRM32_DC0V_25degC_series": "./GRM32_DC0V_25degC_series.s2p"
#     },
#     "SPICEModel": {
#         "GRM32_DC0V_25degC": "./GRM32_DC0V_25degC.mod"
#     },
#     "Definitions": {
#         "CAPC1005X05N": {
#             "Component_type": "Capacitor",
#             "Model_type": "RLC",
#             "Res": 1,
#             "Ind": 2,
#             "Cap": 3,
#             "Is_parallel": false
#         },
#         "'CAPC3216X180X55ML20T25": {
#             "Component_type": "Capacitor",
#             "Model_type": "SParameterModel",
#             "Model_name": "GRM32_DC0V_25degC_series"
#         },
#         "'CAPC3216X180X20ML20": {
#             "Component_type": "Capacitor",
#             "Model_type": "SPICEModel",
#             "Model_name": "GRM32_DC0V_25degC"
#         }
#     }
# }

edbapp.components.import_definition(os.path.join(target_aedb, "1_comp_definition.json"))

###############################################################################
# Import BOM
# ~~~~~~~~~~
# This step imports a BOM file in CSV format. The BOM contains the
# reference designator, part name, component type, and default value.
# Components not in the BOM are deactivated.
# In this example the csv file is stored for convenience in aedb folder.
#
# +------------+-----------------------+-----------+------------+
# | RefDes     | Part name             | Type      | Value      |
# +============+=======================+===========+============+
# | C380       | CAPC1005X55X25LL05T10 | Capacitor | 11nF       |
# +------------+-----------------------+-----------+------------+


edbapp.components.import_bom(os.path.join(target_aedb, "0_bom.csv"),
                                  refdes_col=0,
                                  part_name_col=1,
                                  comp_type_col=2,
                                  value_col=3)



###############################################################################
# Check Component Values
# ~~~~~~~~~~~~~~~~~~~~~~
# Component property allows to access all components instances and their property with getters and setters.

comp = edbapp.components["C1"]
comp.model_type, comp.value


###############################################################################
# Check Component Definition
# ~~~~~~~~~~~~~~~~~~~~~~~~~~
# When an s-parameter model is associated to a component it will be available in nport_comp_definition property.

edbapp.components.nport_comp_definition

###############################################################################
# Save Edb
# ~~~~~~~~
edbapp.save_edb()

###############################################################################
# Configure Setup
# ~~~~~~~~~~~~~~~
# This step allows to define the project. It includes:
#  - Definition of nets to be included into the cutout,
#  - Cutout details,
#  - Components on which to create the ports,
#  - Simulation settings.

sim_setup = edbapp.new_simulation_configuration()
sim_setup.solver_type = sim_setup.SOLVER_TYPE.SiwaveSYZ
sim_setup.batch_solve_settings.cutout_subdesign_expansion = 0.003
sim_setup.batch_solve_settings.do_cutout_subdesign = True
sim_setup.batch_solve_settings.use_pyaedt_cutout = True
sim_setup.ac_settings.max_arc_points = 6
sim_setup.ac_settings.max_num_passes = 5

sim_setup.batch_solve_settings.signal_nets = ['PCIe_Gen4_TX2_CAP_P',
                                              'PCIe_Gen4_TX2_CAP_N',
                                              'PCIe_Gen4_TX2_P',
                                              'PCIe_Gen4_TX2_N']
sim_setup.batch_solve_settings.components = ["U1", "X1"]
sim_setup.batch_solve_settings.power_nets = ["GND", "GND_DP"]
sim_setup.ac_settings.start_freq = "100Hz"
sim_setup.ac_settings.stop_freq = "6GHz"
sim_setup.ac_settings.step_freq = "10MHz"

###############################################################################
# Run Setup
# ~~~~~~~~~
# This step allows to create the cutout and apply all settings.

sim_setup.export_json(os.path.join(project_path, "configuration.json"))
edbapp.build_simulation_project(sim_setup)

###############################################################################
# Plot Cutout
# ~~~~~~~~~~~
# Plot cutout once finished.

edbapp.nets.plot(None,None)

###############################################################################
# Save and Close EDB
# ~~~~~~~~~~~~~~~~~~
# Edb will be saved and closed in order to be opened by Hfss 3D Layout and solved.

edbapp.save_edb()
edbapp.close_edb()

###############################################################################
# Open Aedt
# ~~~~~~~~~
# Project folder aedb will be opened in AEDT Hfss3DLayout and loaded.
h3d = pyaedt.Hfss3dLayout(specified_version="2023.2", projectname=target_aedb, non_graphical=non_graphical, new_desktop_session=True)

###############################################################################
# Analyze
# ~~~~~~~
# Project will be solved.
h3d.analyze()

###############################################################################
# Get Results
# ~~~~~~~~~~~
# S Parameter data will be loaded at the end of simulation.
solutions = h3d.post.get_solution_data()

###############################################################################
# Plot Results
# ~~~~~~~~~~~~
# Plot S Parameter data.
solutions.plot(solutions.expressions, "db20")

###############################################################################
# Save and Close AEDT
# ~~~~~~~~~~~~~~~~~~~
# Hfss3dLayout is saved and closed.
h3d.save_project()
h3d.release_desktop()
