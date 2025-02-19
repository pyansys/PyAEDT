# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 - 2025 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Extension template to help get started

from pathlib import Path
import tkinter as tk
import tkinter.ttk as ttk

import PIL.Image
import PIL.ImageTk
import ansys.aedt.core
from ansys.aedt.core.workflows.misc import ExtensionTheme
from ansys.aedt.core.workflows.misc import get_aedt_version
from ansys.aedt.core.workflows.misc import get_arguments
from ansys.aedt.core.workflows.misc import get_port
from ansys.aedt.core.workflows.misc import get_process_id
from ansys.aedt.core.workflows.misc import is_student
from pyedb.generic.general_methods import generate_unique_name

port = get_port()
version = get_aedt_version()
aedt_process_id = get_process_id()
is_student = is_student()

# Extension batch arguments
VERSION = "0.1.0"
extension_description = f"Layout Design Toolkit ({VERSION})"

default_config_add_antipad = {"selections": [], "radius": "0.5mm", "race_track": True}


class Frontend:  # pragma: no cover
    class UIAntipad:

        def __init__(self, master_ui):
            self.master_ui = master_ui

            self.selection_var = tk.StringVar()
            self.radius_var = tk.StringVar()
            self.race_track_var = tk.BooleanVar()

            self.selection_var.set("")
            self.radius_var.set("0.5mm")
            self.race_track_var.set(True)

        def create_ui(self, master):
            # Selection entry
            row = 0
            selections_label = ttk.Label(master, text="Vias", width=20, style="PyAEDT.TLabel")
            selections_label.grid(row=row, column=0, padx=15, pady=10)
            selections_entry = tk.Entry(master, width=40, textvariable=self.selection_var)
            selections_entry.grid(row=row, column=1, pady=15, padx=10)
            selections_button = ttk.Button(
                master,
                text="Get Selections",
                command=lambda: self.master_ui.get_selections(self.selection_var),
                width=20,
                style="PyAEDT.TButton",
            )
            selections_button.grid(row=row, column=2, pady=15, padx=10)

            # radius
            radius_label = ttk.Label(master, text="Anti pad radius", width=20, style="PyAEDT.TLabel")
            radius_label.grid(row=1, column=0, padx=15, pady=10)
            radius_entry = tk.Entry(master, width=40, textvariable=self.radius_var)
            radius_entry.grid(row=1, column=1, pady=15, padx=10)

            cb = ttk.Checkbutton(master, text="RaceTrack", variable=self.race_track_var, style="PyAEDT.TCheckbutton")
            cb.grid(row=1, column=2, pady=15, padx=10)

            b = ttk.Button(master, text="Create", command=self.callback, style="PyAEDT.TButton")
            b.grid(row=6, column=0, padx=15, pady=10)

        def callback(self):
            selected = self.selection_var.get().split(",")
            if not len(selected) == 2:
                self.selection_var.set("Please select two vias")
                return

            h3d = self.master_ui.get_h3d
            backend = BackendAntipad(h3d)
            backend.create(
                selected,
                self.radius_var.get(),
                self.race_track_var.get(),
            )
            h3d.release_desktop(False, False)

    class UIMicroVia:
        def __init__(self, master_ui):
            self.master_ui = master_ui

            self.selection_var = tk.StringVar()
            self.only_signal_var = tk.BooleanVar()
            self.angle = tk.DoubleVar()

            self.only_signal_var.set(True)
            self.angle.set(15)

        def create_ui(self, master):
            grid_params = {"padx": 15, "pady": 15}

            row = 0
            label = ttk.Label(master, text="Padstack Def", width=20, style="PyAEDT.TLabel")
            label.grid(row=row, column=0, **grid_params)
            entry = tk.Entry(master, width=20, textvariable=self.selection_var)
            entry.grid(row=row, column=1, **grid_params)
            button = ttk.Button(
                master, text="Get Selection", command=self.get_padstack_def, width=20, style="PyAEDT.TButton"
            )
            button.grid(row=row, column=2, pady=15, padx=10)

            row = row + 1
            label = ttk.Label(master, text="Etching Angle (deg)", width=20, style="PyAEDT.TLabel")
            label.grid(row=row, column=0, **grid_params)
            entry = tk.Entry(master, width=20, textvariable=self.angle)
            entry.grid(row=row, column=1, **grid_params)

            row = row + 1
            checkbox = ttk.Checkbutton(
                master, text="Signal Only", variable=self.only_signal_var, width=20, style="PyAEDT.TCheckbutton"
            )
            checkbox.grid(row=row, column=0, **grid_params)

            row = row + 1
            button = ttk.Button(master, text="Create New Project", command=self.callback, style="PyAEDT.TButton")
            button.grid(row=row, column=0, **grid_params)

        def get_padstack_def(self):
            self.master_ui.get_selections(self.selection_var)
            pedb = self.master_ui.get_h3d.modeler.primitives.edb
            temp = []
            selected = self.selection_var.get().split(",")
            for i in selected:
                inst = pedb.padstacks.instances_by_name[i]
                pdef_name = inst.definition.name
                if pdef_name not in temp:
                    temp.append(pdef_name)
            pedb.close()
            self.selection_var.set(",".join(temp))

        def callback(self):
            selected = self.selection_var.get().split(",")

            h3d = self.master_ui.get_h3d
            backend = BackendMircoVia(h3d)
            new_edb_path = backend.create(
                selected,
                self.only_signal_var.get(),
                self.angle.get(),
            )
            h3d = ansys.aedt.core.Hfss3dLayout(project=new_edb_path)
            h3d.release_desktop(False, False)

    @property
    def active_design(self):
        desktop = ansys.aedt.core.Desktop(
            new_desktop=False,
            specified_version=version,
            port=port,
            aedt_process_id=aedt_process_id,
            student_version=is_student,
        )
        oproject = desktop.active_project()
        odesign = oproject.GetActiveDesign()

        if odesign.GetDesignType() in ["HFSS 3D Layout Design"]:
            return desktop, oproject, odesign

    @property
    def get_h3d(self):
        _, oproject, odesign = self.active_design
        project_name = oproject.GetName()
        design_name = odesign.GetName().split(";")[1]
        return ansys.aedt.core.Hfss3dLayout(project=project_name, design=design_name)

    def __init__(self):
        # Load initial configuration

        # Create UI
        self.master = tk.Tk()
        master = self.master
        master.geometry()
        master.title(extension_description)

        # Detect if user close the UI
        master.flag = False

        # Load the logo for the main window
        icon_path = Path(ansys.aedt.core.workflows.__path__[0]) / "images" / "large" / "logo.png"
        im = PIL.Image.open(icon_path)
        photo = PIL.ImageTk.PhotoImage(im)

        # Set the icon for the main window
        master.iconphoto(True, photo)

        # Configure style for ttk buttons
        self.style = ttk.Style()
        self.theme = ExtensionTheme()

        self.theme.apply_light_theme(self.style)
        master.theme = "light"

        # Set background color of the window (optional)
        master.configure(bg=self.theme.light["widget_bg"])
        # Create buttons to create sphere and change theme color

        # Main panel
        main_frame = ttk.PanedWindow(master, orient=tk.VERTICAL, style="TPanedwindow")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Upper panel
        nb = ttk.Notebook(master, style="PyAEDT.TNotebook")

        tab = ttk.Frame(nb, style="PyAEDT.TFrame")
        nb.add(tab, text="Antipad")
        sub_ui = self.UIAntipad(self)
        sub_ui.create_ui(tab)

        tab = ttk.Frame(nb, style="PyAEDT.TFrame")
        nb.add(tab, text="Micro Via")
        sub_ui = self.UIMicroVia(self)
        sub_ui.create_ui(tab)

        main_frame.add(nb, weight=1)

        # Lower panel
        lower_frame = ttk.Frame(master, style="PyAEDT.TFrame")
        main_frame.add(lower_frame, weight=3)

        self.change_theme_button = ttk.Button(
            lower_frame, text="\u263D", width=2, command=self.toggle_theme, style="PyAEDT.TButton"
        )
        self.change_theme_button.pack(side=tk.RIGHT, pady=10, padx=20)

        self.set_dark_theme()
        tk.mainloop()

    def toggle_theme(self):
        master = self.master
        if master.theme == "light":
            self.set_dark_theme()
            master.theme = "dark"
        else:
            self.set_light_theme()
            master.theme = "light"

    def set_light_theme(self):
        self.master.configure(bg=self.theme.light["widget_bg"])
        self.theme.apply_light_theme(self.style)
        self.change_theme_button.config(text="\u263D")

    def set_dark_theme(self):
        self.master.configure(bg=self.theme.dark["widget_bg"])
        self.theme.apply_dark_theme(self.style)
        self.change_theme_button.config(text="\u2600")

    def get_selections(self, text_var):
        desktop, _, odesign = self.active_design
        selected = odesign.GetEditor("Layout").GetSelections()
        desktop.release_desktop(False, False)
        text_var.set(",".join(selected))
        return selected


class BackendBase:
    def __init__(self, h3d):

        self.h3d = h3d
        self.pedb = h3d.modeler.primitives.edb

    def create_line_void(self, owner, layer_name, path, width):
        void_name = generate_unique_name("line_void_")
        temp = []
        for i in path:
            temp.append("x:=")
            temp.append(i[0])
            temp.append("y:=")
            temp.append(i[1])

        line_void_geometry = [
            "Name:=",
            void_name,
            "LayerName:=",
            layer_name,
            "lw:=",
            width,
            "endstyle:=",
            0,
            "StartCap:=",
            2,
            "EndCap:=",
            2,
            "n:=",
            2,
            "U:=",
            "meter",
        ]
        line_void_geometry.extend(temp)
        line_void_geometry.extend(["MR:=", "600mm"])
        args = ["NAME:Contents", "owner:=", owner, "line voidGeometry:=", line_void_geometry]
        self.h3d.oeditor.CreateLineVoid(args)

    def create_circle_void(self, owner, layer_name, center_point, radius):
        args = [
            "NAME:Contents",
            "owner:=",
            owner,
            "circle voidGeometry:=",
            [
                "Name:=",
                generate_unique_name("circle_void_"),
                "LayerName:=",
                layer_name,
                "lw:=",
                "0",
                "x:=",
                center_point[0],
                "y:=",
                center_point[1],
                "r:=",
                radius,
            ],
        ]
        self.h3d.oeditor.CreateCircleVoid(args)


class BackendAntipad(BackendBase):
    def __init__(self, h3d):
        BackendBase.__init__(self, h3d)

    def get_primitives(self, via_p, via_n):
        via_range = via_p.layer_range_names

        prims = {}
        for i in self.pedb.layout.primitives:
            if i.primitive_type in ["rectangle", "polygon"]:
                for pos in [via_p.position, via_n.position]:
                    if i.polygon_data.point_in_polygon(pos[0], pos[1]):
                        if i.layer_name not in via_range:
                            continue
                        if i.layer_name not in prims:
                            prims[i.layer_name] = [i]
                        else:  # pragma: no cover
                            prims[i.layer_name].append(i)
                        break
        return prims

    def create(self, selections, radius, race_track):
        via_p = self.pedb.padstacks.instances_by_name[selections[0]]
        via_n = self.pedb.padstacks.instances_by_name[selections[1]]

        variable_name = f"{via_p.net_name}_{via_p.name}_{via_n.name}_antipad_radius"
        if variable_name not in self.h3d.variable_manager.variable_names:
            self.h3d[variable_name] = radius
        planes = self.get_primitives(via_p, via_n)

        for _, obj_list in planes.items():
            for obj in obj_list:
                if race_track:
                    self.create_line_void(
                        obj.aedt_name, obj.layer_name, [via_p.position, via_n.position], f"{variable_name}*2"
                    )
                else:
                    self.create_circle_void(obj.aedt_name, obj.layer_name, via_p.position, variable_name)
                    self.create_circle_void(obj.aedt_name, obj.layer_name, via_n.position, variable_name)
        self.pedb.close()
        print("***** Done *****")


class BackendMircoVia(BackendBase):
    def __init__(self, h3d):
        BackendBase.__init__(self, h3d)

    def create(self, selection, signal_only, angle):
        for i in selection:
            self.pedb.padstacks[i].convert_to_3d_microvias(
                convert_only_signal_vias=signal_only, hole_wall_angle=angle, delete_padstack_def=True
            )

        edb_path = Path(self.pedb.edbpath)

        new_path = str(edb_path.with_stem(generate_unique_name(edb_path.stem)))
        self.pedb.save_as(new_path)
        self.pedb.close()
        return new_path


if __name__ == "__main__":  # pragma: no cover
    args = get_arguments({}, extension_description)
    # Open UI
    if not args["is_batch"]:  # pragma: no cover
        Frontend()
