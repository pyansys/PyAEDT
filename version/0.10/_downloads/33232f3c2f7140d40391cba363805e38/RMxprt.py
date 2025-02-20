"""
Rmxprt: Create and export motor
-------------------------------
This example uses PyAEDT to create an Rmxprt project and export to Maxwell 2D
Keywords: Rmxprt, Maxwell2D
"""
import os.path
import tempfile

import ansys.aedt.core


##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.2"
temp_dir = tempfile.TemporaryDirectory(suffix=".ansys")

##################################################################################
# Launch AEDT and Rmxprt
# ~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT and Rmxprt after first setting up the project name.
# As solution type we will use ASSM (Adjust-Speed Syncronous Machine).


app = ansys.aedt.core.Rmxprt(
    version=aedt_version,
    new_desktop=True,
    close_on_exit=True,
    solution_type="ASSM",
    project=os.path.join(temp_dir.name, "ASSM.aedt"),
)

##################################################################################
# Define Machine settings
# ~~~~~~~~~~~~~~~~~~~~~~~
# Define global machine settings.

app.general["Number of Poles"] = 4
app.general["Rotor Position"] = "Inner Rotor"
app.general["Frictional Loss"] = "12W"
app.general["Windage Loss"] = "0W"
app.general["Reference Speed"] = "1500rpm"
app.general["Control Type"] = "DC"
app.general["Circuit Type"] = "Y3"


##################################################################################
# Define circuit settings
# ~~~~~~~~~~~~~~~~~~~~~~~
# Define circuit settings.

app.circuit["Trigger Pulse Width"] = "120deg"
app.circuit["Transistor Drop"] = "2V"
app.circuit["Diode Drop"] = "2V"


##################################################################################
# Stator
# ~~~~~~
# Define stator, slot and windings settings.

app.stator["Outer Diameter"] = "122mm"
app.stator["Inner Diameter"] = "75mm"
app.stator["Length"] = "65mm"
app.stator["Stacking Factor"] = 0.95
app.stator["Steel Type"] = "steel_1008"
app.stator["Number of Slots"] = 24
app.stator["Slot Type"] = 2

app.stator.properties.children["Slot"].props["Auto Design"] = False
app.stator.properties.children["Slot"].props["Hs0"] = "0.5mm"
app.stator.properties.children["Slot"].props["Hs1"] = "1.2mm"
app.stator.properties.children["Slot"].props["Hs2"] = "8.2mm"
app.stator.properties.children["Slot"].props["Bs0"] = "2.5mm"
app.stator.properties.children["Slot"].props["Bs1"] = "5.6mm"
app.stator.properties.children["Slot"].props["Bs2"] = "7.6mm"

app.stator.properties.children["Winding"].props["Winding Layers"] = 2
app.stator.properties.children["Winding"].props["Parallel Branches"] = 1
app.stator.properties.children["Winding"].props["Conductors per Slot"] = 52
app.stator.properties.children["Winding"].props["Coil Pitch"] = 5
app.stator.properties.children["Winding"].props["Number of Strands"] = 1

##################################################################################
# Rotor
# ~~~~~
# Define rotor and pole settings.

app.rotor["Outer Diameter"] = "74mm"
app.rotor["Inner Diameter"] = "26mm"
app.rotor["Length"] = "65mm"
app.rotor["Stacking Factor"] = 0.95
app.rotor["Steel Type"] = "steel_1008"
app.rotor["Pole Type"] = 1

app.rotor.properties.children["Pole"].props["Embrace"] = 0.7
app.rotor.properties.children["Pole"].props["Offset"] = 0
app.rotor.properties.children["Pole"].props["Magnet Type"] = ["Material:=", "Alnico9"]
app.rotor.properties.children["Pole"].props["Magnet Thickness"] = "3.5mm"

##################################################################################
# Setup
# ~~~~~
# Create a setup and define main settings.

setup = app.create_setup()
setup.props["RatedVoltage"] = "220V"
setup.props["RatedOutputPower"] = "550W"
setup.props["RatedSpeed"] = "1500rpm"
setup.props["OperatingTemperature"] = "75cel"


setup.analyze()

##################################################################################
# Export to Maxwell
# ~~~~~~~~~~~~~~~~~
# After the project is solved we can export in Maxwell 2D or Maxwell 3D.

m2d = app.create_maxwell_design(setup_name=setup.name, maxwell_2d=True)

m2d.plot(show=False, output_file=os.path.join(temp_dir.name, "Image.jpg"), plot_air_objects=True)


##################################################################################
# Rmxprt settings export
# ~~~~~~~~~~~~~~~~~~~~~~
# All Rmxprt settings can be exported in a json file and reused for another
# project with import function.

config = app.export_configuration(os.path.join(temp_dir.name, "assm.json"))
app2 = ansys.aedt.core.Rmxprt(project="assm_test2",solution_type=app.solution_type, design="from_configuration")
app2.import_configuration(config)



##################################################################################
# Save and Close Desktop
# ~~~~~~~~~~~~~~~~~~~~~~
# Save and Close Desktop.

m2d.save_project(os.path.join(temp_dir.name, "Maxwell_project.aedt"))

m2d.release_desktop()

##########################
# Cleanup
# ~~~~~~~
#
# All project files are saved in the folder ``temp_dir.name``. If you've run this example as a Jupyter notebook you
# can retrieve those project files. The following cell removes all temporary files, including the project folder.

temp_dir.cleanup()