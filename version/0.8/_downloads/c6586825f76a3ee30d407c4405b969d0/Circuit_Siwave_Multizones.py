"""
Circuit: Simulate multi-zones layout with Siwave
------------------------------------------------
This example shows how you can use PyAEDT simulate multi-zones with Siwave.
"""

###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports, which includes importing a section.

from pyaedt import Edb, Circuit
import os.path
import pyaedt

###############################################################################
# Download file
# ~~~~~~~~~~~~~
# Download the AEDB file and copy it in the temporary folder.

temp_folder = pyaedt.generate_unique_folder_name()
edb_file = pyaedt.downloads.download_file(destination=temp_folder, directory="edb/siwave_multi_zones.aedb")
working_directory = os.path.join(temp_folder, "workdir")
aedt_file = os.path.splitext(edb_file)[0] + ".aedt"
circuit_project_file = os.path.join(working_directory, os.path.splitext(os.path.basename(edb_file))[0] +
                               "multizone_clipped_circuit.aedt")
print(edb_file)


##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

#####################################################################################
# Ground net
# ~~~~~~~~~~
# Common reference net used across all sub-designs, Mandatory for this work flow.

common_reference_net = "GND"

########################################################################################
# Project load
# ~~~~~~~~~~~~
# Load initial Edb file, checking if aedt file exists and remove to allow Edb loading.

if os.path.isfile(aedt_file):
    os.remove(aedt_file)
edb = Edb(edbversion=aedt_version, edbpath=edb_file)

###############################################################################
# Project zones
# ~~~~~~~~~~~~~
# Copy project zone into sub project.

edb_zones = edb.copy_zones(working_directory=working_directory)

###############################################################################
# Split zones
# ~~~~~~~~~~~
# Clip sub-designs along with corresponding zone definition
# and create port of clipped signal traces.
defined_ports, project_connexions = edb.cutout_multizone_layout(edb_zones, common_reference_net)

#############################################################################################################
# Circuit
# ~~~~~~~
# Create circuit design, import all sub-project as EM model and connect all corresponding pins in circuit.

circuit = Circuit(specified_version=aedt_version, projectname=circuit_project_file)
circuit.connect_circuit_models_from_multi_zone_cutout(project_connections=project_connexions,
                                                      edb_zones_dict=edb_zones, ports=defined_ports,
                                                      model_inc=70)
###############################################################################
# Setup
# ~~~~~
#  Add Nexxim LNA simulation setup.
circuit_setup= circuit.create_setup("Pyedt_LNA")

###############################################################################
# Frequency sweep
# ~~~~~~~~~~~~~~~
# Add frequency sweep from 0GHt to 20GHz with 10NHz frequency step.
circuit_setup.props["SweepDefinition"]["Data"] = "LIN {} {} {}".format("0GHz", "20GHz", "10MHz")

###############################################################################
# Start simulation
# ~~~~~~~~~~~~~~~~
# Analyze all siwave projects and solves the circuit.
circuit.analyze()

###############################################################################
# Define differential pairs
# ~~~~~~~~~~~~~~~~~~~~~~~~~
circuit.set_differential_pair(assignment="U0.via_38.B2B_SIGP", reference="U0.via_39.B2B_SIGN", differential_mode="U0")
circuit.set_differential_pair(assignment="U1.via_32.B2B_SIGP", reference="U1.via_33.B2B_SIGN", differential_mode="U1")

###############################################################################
# Plot results
# ~~~~~~~~~~~~
circuit.post.create_report(expressions=["dB(S(U0,U0))", "dB(S(U1,U0))"], context="Differential Pairs")

###############################################################################
# Release AEDT desktop
# ~~~~~~~~~~~~~~~~~~~~
circuit.release_desktop()