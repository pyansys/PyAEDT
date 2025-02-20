# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 - 2024 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
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

import os
import sys
import subprocessdotnet as subprocess

# This script installs PyAEDT tabs (PyAEDT Console, Jupyter, Run Script and Extension Manager)
# using a specific Python interpreter.
# It can be passed from an environment variable called "PYAEDT_INTERPRETER" or from the input argument.
# The environment variable has more priority.

is_linux = os.name == "posix"
is_windows = not is_linux

pyaedt_enviroment_variable = "PYAEDT_INTERPRETER"


def run_pyinstaller_from_c_python(oDesktop, pyaedt_interpreter):
    # Iron Python script to create PyAEDT panels

    # Get AEDT information
    version = oDesktop.GetVersion()[2:6].replace(".", "")

    # Add PyAEDT tabs in AEDT

    # Create Toolkits in PersonalLib
    import tempfile
    python_script = os.path.join(tempfile.gettempdir(), "configure_pyaedt.py")
    if os.path.isfile(python_script):
        os.remove(python_script)
    with open(python_script, "w") as f:
        f.write("from ansys.aedt.core.workflows.installer.pyaedt_installer import add_pyaedt_to_aedt\n")
        f.write(
            'add_pyaedt_to_aedt(aedt_version="{}", personal_lib=r"{}")\n'.format(
                oDesktop.GetVersion()[:6], oDesktop.GetPersonalLibDirectory()))

    command = [pyaedt_interpreter, python_script]
    oDesktop.AddMessage("", "", 0, "Configuring PyAEDT panels in automation tab.")
    process = subprocess.Popen(command)
    process.wait()

    # Refresh UI
    oDesktop.CloseAllWindows()
    if version >= "232":
        oDesktop.RefreshToolkitUI()
    msg = "PyAEDT configuration complete."
    if is_linux:
        msg += " Please ensure Ansys Electronics Desktop is launched in gRPC mode (i.e. launch ansysedt with -grpcsrv" \
               " argument) to take advantage of the new toolkits."

    if "GetIsNonGraphical" in oDesktop.__dir__() and not oDesktop.GetIsNonGraphical():
        from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon
        oDesktop.AddMessage("", "", 0, msg)
        MessageBox.Show(msg, 'Info', MessageBoxButtons.OK, MessageBoxIcon.Information)
    oDesktop.AddMessage("", "", 0, "Create a project if the PyAEDT panel is not visible.")


if __name__ == "__main__":

    python_interpreter = os.getenv(pyaedt_enviroment_variable)
    if python_interpreter and not os.path.exists(python_interpreter):
        oDesktop.AddMessage("", "", 2, "Python environment does not exist.")
        sys.exit()

    # Check if interpreter path is defined.
    # Retrieve the script arguments
    script_args = ScriptArgument.split()
    if len(script_args) == 1 and not python_interpreter:
        python_interpreter = script_args[0]
        if not os.path.exists(python_interpreter):
            oDesktop.AddMessage("", "", 2, "Python environment does not exist.")
            sys.exit()

    if not python_interpreter:
        oDesktop.AddMessage("", "", 2, "Invalid python environment.")
        sys.exit()

    run_pyinstaller_from_c_python(oDesktop, python_interpreter)
