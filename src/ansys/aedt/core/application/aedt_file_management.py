# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 - 2025 ANSYS, Inc. and/or its affiliates.
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

import csv
import os
import re
import shutil

from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler


@pyaedt_function_handler()
def read_info_fromcsv(projdir, name):
    """Read information from a CSV file and return a list.

    Parameters
    ----------
    projdir : str
        Full path to the file.
    name : str
        Name of the file.

    Returns
    -------
    list

    """

    filename = projdir + "//" + name
    rows = []
    with open_file(filename, "r", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        for row in reader:
            rows.append(row)
    return rows


@pyaedt_function_handler()
def clean_proj_folder(dir, name):
    """Delete all project name-related folders.

    Parameters
    ----------
    dir : str
        Full path to the project directory.
    name : str
        Name of the project.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    if os.path.exists(dir):
        shutil.rmtree(dir, True)
    os.mkdir(dir)
    return True


@pyaedt_function_handler()
def create_output_folder(ProjectDir):
    """Create the output folders starting from the project directory.

    Parameters
    ----------
    ProjectDir : str
        Name of the project directory.

    Returns
    -------
    type
        PicturePath, ResultsPath

    """
    npath = os.path.normpath(ProjectDir)
    base = os.path.basename(npath)

    # set pathname for the Output
    output_path = os.path.join(npath, base)
    # set pathname for the images
    picture_path = os.path.join(output_path, "Pictures")
    # set pathname for the files
    results_path = os.path.join(output_path, "Results")

    # Add folders for outputs
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(picture_path, exist_ok=True)
    os.makedirs(results_path, exist_ok=True)
    return picture_path, results_path


@pyaedt_function_handler()
def change_objects_visibility(origfile, solid_list):
    """Edit the project file to make only the solids that are specified visible.

    Parameters
    ----------
    origfile : str
        Full path to the project file, which has an ``.aedt`` extension.
    solid_list : list
        List of names for the solid to make visible. All other solids are hidden.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    path, filename = os.path.split(origfile)
    newfile = os.path.join(path, "aedttmp.tmp")

    if not os.path.isfile(origfile + ".lock"):  # check if the project is closed
        try:
            # Using text mode with explicit encoding instead of binary mode.
            with open(origfile, "r", encoding="utf-8") as f, open(newfile, "w", encoding="utf-8") as n:
                # Reading file content
                content = f.read()

                # Searching file content for pattern
                pattern = re.compile(
                    r"(\$begin 'EditorWindow'\n.+)(Drawings\[.+\])(.+\n\s*\$end 'EditorWindow')", re.UNICODE | re.DOTALL
                )
                # Replacing string
                # fmt: off
                view_str = u"Drawings[" + str(len(solid_list)) + u": " + str(solid_list).strip("[")
                s = pattern.sub(r"\1" + view_str + r"\3", content)
                # fmt: on
                # Writing file content
                n.write(s)
            # Renaming files and deleting temporary file
            os.remove(origfile)
            os.rename(newfile, origfile)
            return True
        except Exception as e:
            # Cleanup temporary file if exists.
            if os.path.exists(newfile):
                os.remove(newfile)
            print("change_objects_visibility: Error encountered -", e)
            return False
    else:  # project is locked
        print("change_objects_visibility: Project %s is still locked." % origfile)
        return False


@pyaedt_function_handler()
def change_model_orientation(origfile, bottom_dir):
    """Edit the project file to change the model orientation.

    Parameters
    ----------
    origfile : str
        Full path to the project file, which has an ``.aedt`` extension.
    bottom_dir : str
        Bottom direction as specified in the properties file.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    path, filename = os.path.split(origfile)
    newfile = os.path.join(path, "aedttmp.tmp")

    # directory of u, v vectors for view orientation
    orientation = {
        "+X": "OrientationMatrix(0, -0.816496610641479, -0.577350318431854, 0, 0.70710676908493, -0.40824830532074, "
        "0.577350318431854, 0, -0.70710676908493, -0.40824830532074, 0.577350318431854, 0, 0, 0, 0, 1, 0, -100, "
        "100, -100, 100, -100, 100)",
        "+Y": "OrientationMatrix(-0.70710688829422, -0.408248245716095, 0.577350199222565, 0, 1.04308128356934e-07, "
        "-0.816496670246124, -0.577350199222565, 0, 0.707106709480286, -0.408248245716095, 0.577350437641144, "
        "0, 0, 0, 0, 1, 0, -100, 100, -100, 100, -100, 100)",
        "+Z": "OrientationMatrix(0.70710676908493, -0.408248394727707, 0.577350199222565, 0, -0.70710676908493, "
        "-0.408248394727707, 0.577350199222565, 0, 0, -0.81649649143219, -0.577350437641144, 0, 0, 0, 0, 1, 0, "
        "-100, 100, -100, 100, -100, 100)",
        "-X": "OrientationMatrix(0, 0.816496610641479, 0.577350318431854, 0, -0.70710676908493, -0.40824830532074, "
        "0.577350318431854, 0, 0.70710676908493, -0.40824830532074, 0.577350318431854, 0, 0, 0, -0, 1, 0, -100, "
        "100, -100, 100, -100, 100)",
        "-Y": "OrientationMatrix(0.70710688829422, -0.408248245716095, 0.577350199222565, 0, 1.04308128356934e-07, "
        "0.816496670246124, 0.577350199222565, 0, -0.707106709480286, -0.408248245716095, 0.577350437641144, 0, "
        "0, 0, -0, 1, 0, -100, 100, -100, 100, -100, 100)",
        "-Z": "OrientationMatrix(-0.70710676908493, -0.408248394727707, 0.577350199222565, 0, 0.70710676908493, "
        "-0.408248394727707, 0.577350199222565, 0, 0, 0.81649649143219, 0.577350437641144, 0, 0, 0, -0, 1, 0, "
        "-100, 100, -100, 100, -100, 100) ",
    }

    if not os.path.isfile(origfile + ".lock"):  # check if the project is closed
        try:
            # Using text mode with explicit encoding.
            with open(origfile, "r", encoding="utf-8") as f, open(newfile, "w", encoding="utf-8") as n:
                # Reading file content
                content = f.read()

                # Searching file content for pattern
                pattern = re.compile(
                    r"(\$begin 'EditorWindow'\n.+?)(OrientationMatrix\(.+?\))(.+\n\s*\$end 'EditorWindow')",
                    re.UNICODE | re.DOTALL,
                )
                # Replacing string
                orientation_str = orientation.get(bottom_dir, "")
                s = pattern.sub(r"\1" + orientation_str + r"\3", content)

                # Writing file content
                n.write(s)
            # Renaming files and deleting temporary file
            os.remove(origfile)
            os.rename(newfile, origfile)
            return True
        except Exception as e:
            if os.path.exists(newfile):
                os.remove(newfile)
            print("change_model_orientation: Error encountered -", e)
            return False
    else:  # Project is locked
        print("change_model_orientation: Project %s is still locked." % origfile)
        return False
