"""
2D Extractor: CPWG analysis
---------------------------
This example shows how you can use PyAEDT to create a CPWG (coplanar waveguide with ground) design
in 2D Extractor and run a simulation.
"""
###############################################################################
# Perform required imports
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Perform required imports.

import os
import pyaedt

###############################################################################
# Set non-graphical mode
# ~~~~~~~~~~~~~~~~~~~~~~
# Set non-graphical mode. 
# You can set ``non_graphical`` either to ``True`` or ``False``.

non_graphical = False
desktop_version = "2023.2"
###############################################################################
# Launch AEDT and 2D Extractor
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Launch AEDT 2023 R2 in graphical mode and launch 2D Extractor. This example
# uses SI units.

q = pyaedt.Q2d(specified_version=desktop_version,
               non_graphical=non_graphical,
               new_desktop_session=True,
               projectname=pyaedt.generate_unique_name("pyaedt_q2d_example"),
               designname="coplanar_waveguide")

###############################################################################
# Define variables
# ~~~~~~~~~~~~~~~~
# Define variables.

e_factor = "e_factor"
sig_bot_w = "sig_bot_w"
co_gnd_w = "gnd_w"
clearance = "clearance"
cond_h = "cond_h"
d_h = "d_h"
sm_h = "sm_h"

for var_name, var_value in {
    "sig_bot_w": "150um",
    "e_factor": "2",
    "gnd_w": "500um",
    "clearance": "150um",
    "cond_h": "50um",
    "d_h": "150um",
    "sm_h": "20um",
}.items():
    q[var_name] = var_value

delta_w_half = "({0}/{1})".format(cond_h, e_factor)
sig_top_w = "({1}-{0}*2)".format(delta_w_half, sig_bot_w)
co_gnd_top_w = "({1}-{0}*2)".format(delta_w_half, co_gnd_w)
model_w = "{}*2+{}*2+{}".format(co_gnd_w, clearance, sig_bot_w)

###############################################################################
# Create primitives
# ~~~~~~~~~~~~~~~~~
# Create primitives and define the layer heights.

layer_1_lh = 0
layer_1_uh = cond_h
layer_2_lh = layer_1_uh + "+" + d_h
layer_2_uh = layer_2_lh + "+" + cond_h

###############################################################################
# Create signal
# ~~~~~~~~~~~~~
# Create a signal.

base_line_obj = q.modeler.create_polyline(position_list=[[0, layer_2_lh, 0], [sig_bot_w, layer_2_lh, 0]], name="signal")
top_line_obj = q.modeler.create_polyline(position_list=[[0, layer_2_uh, 0], [sig_top_w, layer_2_uh, 0]])
q.modeler.move(objid=[top_line_obj], vector=[delta_w_half, 0, 0])
q.modeler.connect([base_line_obj, top_line_obj])
q.modeler.move(objid=[base_line_obj], vector=["{}+{}".format(co_gnd_w, clearance), 0, 0])

###############################################################################
# Create coplanar ground
# ~~~~~~~~~~~~~~~~~~~~~~
# Create a coplanar ground.

base_line_obj = q.modeler.create_polyline(position_list=[[0, layer_2_lh, 0], [co_gnd_w, layer_2_lh, 0]],
                                          name="co_gnd_left")
top_line_obj = q.modeler.create_polyline(position_list=[[0, layer_2_uh, 0], [co_gnd_top_w, layer_2_uh, 0]])
q.modeler.move(objid=[top_line_obj], vector=[delta_w_half, 0, 0])
q.modeler.connect([base_line_obj, top_line_obj])

base_line_obj = q.modeler.create_polyline(position_list=[[0, layer_2_lh, 0], [co_gnd_w, layer_2_lh, 0]],
                                          name="co_gnd_right")
top_line_obj = q.modeler.create_polyline(position_list=[[0, layer_2_uh, 0], [co_gnd_top_w, layer_2_uh, 0]])
q.modeler.move(objid=[top_line_obj], vector=[delta_w_half, 0, 0])
q.modeler.connect([base_line_obj, top_line_obj])
q.modeler.move(objid=[base_line_obj], vector=["{}+{}*2+{}".format(co_gnd_w, clearance, sig_bot_w), 0, 0])

###############################################################################
# Create reference ground plane
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create a reference ground plane.

q.modeler.create_rectangle(position=[0, layer_1_lh, 0], dimension_list=[model_w, cond_h], name="ref_gnd")

###############################################################################
# Create dielectric
# ~~~~~~~~~~~~~~~~~
# Create a dielectric.

q.modeler.create_rectangle(
    position=[0, layer_1_uh, 0], dimension_list=[model_w, d_h], name="Dielectric", matname="FR4_epoxy"
)

###############################################################################
# Create conformal coating
# ~~~~~~~~~~~~~~~~~~~~~~~~
# Create a conformal coating.

sm_obj_list = []
ids = [1,2,3]
if desktop_version >= "2023.1":
    ids = [0,1,2]

for obj_name in ["signal", "co_gnd_left", "co_gnd_right"]:
    obj = q.modeler.get_object_from_name(obj_name)
    e_obj_list = []
    for i in ids:
        e_obj = q.modeler.create_object_from_edge(obj.edges[i])
        e_obj_list.append(e_obj)
    e_obj_1 = e_obj_list[0]
    q.modeler.unite(e_obj_list)
    new_obj = q.modeler.sweep_along_vector(e_obj_1.id, [0, sm_h, 0])
    sm_obj_list.append(e_obj_1)

new_obj = q.modeler.create_rectangle(position=[co_gnd_w, layer_2_lh, 0], dimension_list=[clearance, sm_h])
sm_obj_list.append(new_obj)

new_obj = q.modeler.create_rectangle(position=[co_gnd_w, layer_2_lh, 0], dimension_list=[clearance, sm_h])
q.modeler.move([new_obj], [sig_bot_w + "+" + clearance, 0, 0])
sm_obj_list.append(new_obj)

sm_obj = sm_obj_list[0]
q.modeler.unite(sm_obj_list)
sm_obj.material_name = "SolderMask"
sm_obj.color = (0, 150, 100)
sm_obj.name = "solder_mask"

###############################################################################
# Assign conductor
# ~~~~~~~~~~~~~~~~
# Assign a conductor to the signal.

obj = q.modeler.get_object_from_name("signal")
q.assign_single_conductor(
    name=obj.name, target_objects=[obj], conductor_type="SignalLine", solve_option="SolveOnBoundary", unit="mm"
)

###############################################################################
# Create reference ground
# ~~~~~~~~~~~~~~~~~~~~~~~
# Create a reference ground.

obj = [q.modeler.get_object_from_name(i) for i in ["co_gnd_left", "co_gnd_right", "ref_gnd"]]
q.assign_single_conductor(
    name="gnd", target_objects=obj, conductor_type="ReferenceGround", solve_option="SolveOnBoundary", unit="mm"
)

###############################################################################
# Assign Huray model on signal
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Assign the Huray model on the signal.

obj = q.modeler.get_object_from_name("signal")
q.assign_huray_finitecond_to_edges(obj.edges, radius="0.5um", ratio=3, name="b_" + obj.name)

###############################################################################
# Create setup, analyze, and plot
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Create the setup, analyze it, and plot solution data.
 
setup = q.create_setup(setupname="new_setup")

sweep = setup.add_sweep(sweepname="sweep1", sweeptype="Discrete")
sweep.props["RangeType"] = "LinearStep"
sweep.props["RangeStart"] = "1GHz"
sweep.props["RangeStep"] = "100MHz"
sweep.props["RangeEnd"] = "5GHz"
sweep.props["SaveFields"] = False
sweep.props["SaveRadFields"] = False
sweep.props["Type"] = "Interpolating"

sweep.update()

q.analyze()

a = q.post.get_solution_data(expressions="Z0(signal,signal)", context="Original")
a.plot()

###############################################################################
# Save project and close AEDT
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Save the project and close AEDT.

home = os.path.expanduser("~")
q.save_project(os.path.join(home, "Downloads", "pyaedt_example", q.project_name + ".aedt"))
q.release_desktop()
