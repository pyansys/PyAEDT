"""
HFSS: choke
-----------
This example shows how you can use PyAEDT to create a choke setup in HFSS.
"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import json
import os
import pyaedt

project_name = pyaedt.generate_unique_project_name(rootname=r"C:\Data\Support\Test", folder_name="choke", project_name="choke")

##########################################################
# Set AEDT version
# ~~~~~~~~~~~~~~~~
# Set AEDT version.

aedt_version = "2024.1"

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False

###############################################################################
# Launch HFSS
# ~~~~~~~~~~~
# Launches HFSS 2023 R2 in graphical mode.

hfss = pyaedt.Hfss(projectname=project_name,
                   specified_version=aedt_version,
                   non_graphical=non_graphical,
                   new_desktop_session=True,
                   solution_type="Terminal")

###############################################################################
# Rules and information of use
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# The dictionary values contain the different parameter values of the core and
# the windings that compose the choke. You must not change the main structure of
# the dictionary. The dictionary has many primary keys, including
# ``"Number of Windings"``, ``"Layer"``, and ``"Layer Type"``, that have
# dictionaries as values. The keys of these dictionaries are secondary keys
# of the dictionary values, such as ``"1"``, ``"2"``, ``"3"``, ``"4"``, and
# ``"Simple"``.
# 
# You must not modify the primary or secondary keys. You can modify only their values.
# You must not change the data types for these keys. For the dictionaries from
# ``"Number of Windings"`` through ``"Wire Section"``, values must be Boolean. Only
# one value per dictionary can be ``True``. If all values are ``True``, only the first one
# remains set to ``True``. If all values are ``False``, the first value is chosen as the
# correct one by default. For the dictionaries from ``"Core"`` through ``"Inner Winding"``,
# values must be strings, floats, or integers.
#
# Descriptions follow for primary keys:
#
# - ``"Number of Windings"``: Number of windings around the core
# - ``"Layer"``: Number of layers of all windings
# - ``"Layer Type"``: Whether layers of a winding are linked to each other
# - ``"Similar Layer"``: Whether layers of a winding have the same number of turns and same spacing between turns
# - ``"Mode"``: When there are only two windows, whether they are in common or differential mode
# - ``"Wire Section"``: Type of wire section and number of segments
# - ``"Core"``: Design of the core
# - ``"Outer Winding"``: Design of the first layer or outer layer of a winding and the common parameters for all layers
# - ``"Mid Winding"``: Turns and turns spacing ("Coil Pit") for the second or mid layer if it is necessary
# - ``"Inner Winding"``: Turns and turns spacing ("Coil Pit") for the third or inner layer if it is necessary
# - ``"Occupation(%)"``: An informative parameter that is useless to modify
#
# The following parameter values work. You can modify them if you want.

values = {
    "Number of Windings": {"1": False, "2": True, "3": False, "4": False},
    "Layer": {"Simple": False, "Double": True, "Triple": False},
    "Layer Type": {"Separate": False, "Linked": True},
    "Similar Layer": {"Similar": False, "Different": True},
    "Mode": {"Differential": False, "Common": True},
    "Wire Section": {"None": False, "Hexagon": True, "Octagon": False, "Circle": False},
    "Core": {
        "Name": "Core",
        "Material": "ferrite",
        "Inner Radius": 20,
        "Outer Radius": 30,
        "Height": 10,
        "Chamfer": 0.8,
    },
    "Outer Winding": {
        "Name": "Winding",
        "Material": "copper",
        "Inner Radius": 20,
        "Outer Radius": 30,
        "Height": 10,
        "Wire Diameter": 1.5,
        "Turns": 20,
        "Coil Pit(deg)": 0.1,
        "Occupation(%)": 0,
    },
    "Mid Winding": {"Turns": 25, "Coil Pit(deg)": 0.1, "Occupation(%)": 0},
    "Inner Winding": {"Turns": 4, "Coil Pit(deg)": 0.1, "Occupation(%)": 0},
}

###############################################################################
# Convert dictionary to JSON file
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Convert a dictionary to a JSON file. You must supply the path of the
# JSON file as an argument. 

json_path = os.path.join(hfss.working_directory, "choke_example.json")

with open(json_path, "w") as outfile:
    json.dump(values, outfile)

###############################################################################
# Verify parameters of JSON file
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Verify parameters of the JSON file. The ``check_choke_values`` method takes
# the JSON file path as an argument and does the following:
#
# - Checks if the JSON file is correctly written (as explained in the rules)
# - Checks in equations on windings parameters to avoid having unintended intersections

dictionary_values = hfss.modeler.check_choke_values(json_path, create_another_file=False)
print(dictionary_values)

###############################################################################
# Create choke
# ~~~~~~~~~~~~
# Create the choke. The ``create_choke`` method takes the JSON file path as an 
# argument.

list_object = hfss.modeler.create_choke(json_path)
print(list_object)
core = list_object[1]
first_winding_list = list_object[2]
second_winding_list = list_object[3]

###############################################################################
# Create ground
# ~~~~~~~~~~~~~
# Create a ground.

ground_radius = 1.2 * dictionary_values[1]["Outer Winding"]["Outer Radius"]
ground_position = [0, 0, first_winding_list[1][0][2] - 2]
ground = hfss.modeler.create_circle("XY", ground_position, ground_radius, name="GND", material="copper")
coat = hfss.assign_coating(ground, is_infinite_ground=True)

###############################################################################
# Create lumped ports
# ~~~~~~~~~~~~~~~~~~~
# Create lumped ports.

port_position_list = [
    [first_winding_list[1][0][0], first_winding_list[1][0][1], first_winding_list[1][0][2] - 1],
    [first_winding_list[1][-1][0], first_winding_list[1][-1][1], first_winding_list[1][-1][2] - 1],
    [second_winding_list[1][0][0], second_winding_list[1][0][1], second_winding_list[1][0][2] - 1],
    [second_winding_list[1][-1][0], second_winding_list[1][-1][1], second_winding_list[1][-1][2] - 1],
]
port_dimension_list = [2, dictionary_values[1]["Outer Winding"]["Wire Diameter"]]
for position in port_position_list:
    sheet = hfss.modeler.create_rectangle("XZ", position, port_dimension_list, name="sheet_port")
    sheet.move([-dictionary_values[1]["Outer Winding"]["Wire Diameter"] / 2, 0, -1])
    hfss.lumped_port(assignment=sheet.name, reference=[ground],
                     name="port_" + str(port_position_list.index(position) + 1))

###############################################################################
# Create mesh
# ~~~~~~~~~~~
# Create the mesh.

cylinder_height = 2.5 * dictionary_values[1]["Outer Winding"]["Height"]
cylinder_position = [0, 0, first_winding_list[1][0][2] - 4]
mesh_operation_cylinder = hfss.modeler.create_cylinder("XY", cylinder_position, ground_radius, cylinder_height,
                                                       num_sides=36, name="mesh_cylinder")
hfss.mesh.assign_length_mesh([mesh_operation_cylinder], maximum_length=15, maximum_elements=None, name="choke_mesh")


###############################################################################
# Create boundaries
# ~~~~~~~~~~~~~~~~~
# Create the boundaries. A region with openings is needed to run the analysis.

region = hfss.modeler.create_region(pad_percent=1000)


###############################################################################
# Create setup
# ~~~~~~~~~~~~
# Create a setup with a sweep to run the simulation. Depending on your machine's
# computing power, the simulation can take some time to run.

setup = hfss.create_setup("MySetup")
setup.props["Frequency"] = "50MHz"
setup["MaximumPasses"] = 10
hfss.create_linear_count_sweep(setup=setup.name, units="MHz", start_frequency=0.1, stop_frequency=100,
                               num_of_freq_points=100, name="sweep1", save_fields=False, sweep_type="Interpolating")

###############################################################################
# Save project
# ~~~~~~~~~~~~
# Save the project.

hfss.modeler.fit_all()
hfss.plot(show=False, export_path=os.path.join(hfss.working_directory, "Image.jpg"), plot_air_objects=True)


###############################################################################
# Close AEDT
# ~~~~~~~~~~
# After the simulation completes, you can close AEDT or release it using the
# :func:`pyaedt.Desktop.release_desktop` method.
# All methods provide for saving the project before closing.

hfss.release_desktop()
