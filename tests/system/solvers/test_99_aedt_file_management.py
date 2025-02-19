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

import os
from pathlib import Path

import pytest


# Override the desktop fixture so that Desktop is not initialized.
@pytest.fixture(scope="module", autouse=True)
def desktop():
    yield None


from ansys.aedt.core.application.aedt_file_management import change_model_orientation
from ansys.aedt.core.application.aedt_file_management import change_objects_visibility
from ansys.aedt.core.application.aedt_file_management import clean_proj_folder
from ansys.aedt.core.application.aedt_file_management import create_output_folder
from ansys.aedt.core.application.aedt_file_management import read_info_fromcsv


def test_read_info_fromcsv_solver(tmp_path):
    csv_content = "x,y,z\n7,8,9\n10,11,12"
    csv_file = tmp_path / "solver.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    result = read_info_fromcsv(str(tmp_path), "solver.csv")
    expected = [["x", "y", "z"], ["7", "8", "9"], ["10", "11", "12"]]
    assert result == expected


def test_clean_proj_folder_solver(tmp_path):
    project_dir = tmp_path / "solver_project"
    project_dir.mkdir()
    dummy_file = project_dir / "dummy.txt"
    dummy_file.write_text("solver content", encoding="utf-8")

    result = clean_proj_folder(str(project_dir), "solver_project")
    assert result is True
    assert list(project_dir.iterdir()) == []


def test_create_output_folder_solver(tmp_path):
    project_dir = tmp_path / "SolverProject"
    project_dir.mkdir()

    picture_path, results_path = create_output_folder(str(project_dir))

    base = os.path.basename(str(project_dir))
    output_dir = project_dir / base
    assert output_dir.exists() and output_dir.is_dir()
    assert os.path.isdir(picture_path)
    assert os.path.isdir(results_path)


def test_change_objects_visibility_solver(tmp_path):
    content = "$begin 'EditorWindow'\n" "Header\n" "Drawings[old]\n" "Footer\n" "   $end 'EditorWindow'"
    origfile = tmp_path / "solver.aedt"
    origfile.write_text(content, encoding="utf-8")

    lock_file = tmp_path / "solver.aedt.lock"
    if lock_file.exists():
        lock_file.unlink()

    solid_list = ["solver_obj"]
    result = change_objects_visibility(str(origfile), solid_list)
    assert result is True
    new_content = origfile.read_text(encoding="utf-8")
    expected_view_str = "Drawings[" + str(len(solid_list)) + ": " + str(solid_list).strip("[")
    assert expected_view_str in new_content


def test_change_model_orientation_solver(tmp_path):
    content = "$begin 'EditorWindow'\n" "Header\n" "OrientationMatrix(old)\n" "Footer\n" "   $end 'EditorWindow'"
    origfile = tmp_path / "solver.aedt"
    origfile.write_text(content, encoding="utf-8")

    lock_file = tmp_path / "solver.aedt.lock"
    if lock_file.exists():
        lock_file.unlink()

    result = change_model_orientation(str(origfile), "+Z")
    assert result is True
    new_content = origfile.read_text(encoding="utf-8")
    # Ensure that the old orientation is replaced.
    assert "OrientationMatrix(" in new_content and "old" not in new_content
