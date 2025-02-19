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

from ansys.aedt.core.application.aedt_file_management import change_model_orientation
from ansys.aedt.core.application.aedt_file_management import change_objects_visibility
from ansys.aedt.core.application.aedt_file_management import clean_proj_folder
from ansys.aedt.core.application.aedt_file_management import create_output_folder
from ansys.aedt.core.application.aedt_file_management import read_info_fromcsv
import pytest


def test_integration_read_info_fromcsv(tmp_path):
    # Create a temporary CSV file with known content.
    csv_content = "header1,header2\nvalue1,value2"
    csv_file = tmp_path / "data.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    # Call the function.
    result = read_info_fromcsv(str(tmp_path), "data.csv")
    expected = [["header1", "header2"], ["value1", "value2"]]
    assert result == expected


def test_integration_clean_proj_folder(tmp_path):
    # Create a temporary project directory with a dummy file.
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "dummy.txt").write_text("data", encoding="utf-8")

    result = clean_proj_folder(str(project_dir), "project")
    assert result is True
    # The folder is recreated empty.
    assert list(project_dir.iterdir()) == []


def test_integration_create_output_folder(tmp_path):
    # Create a temporary project directory.
    project_dir = tmp_path / "ProjectIntegration"
    project_dir.mkdir()

    picture_path, results_path = create_output_folder(str(project_dir))

    # The output folder is defined as project_dir / basename(project_dir)
    output_dir = project_dir / "ProjectIntegration"
    assert output_dir.exists() and output_dir.is_dir()

    expected_picture = os.path.join(str(output_dir), "Pictures")
    expected_results = os.path.join(str(output_dir), "Results")
    assert picture_path == expected_picture
    assert results_path == expected_results
    assert os.path.isdir(picture_path)
    assert os.path.isdir(results_path)


def test_integration_change_objects_visibility(tmp_path):
    # Create a temporary AEDT file with multiline content.
    content = "$begin 'EditorWindow'\n" "Header info\n" "Drawings[old_value]\n" "Footer info\n" "   $end 'EditorWindow'"
    origfile = tmp_path / "integration.aedt"
    origfile.write_text(content, encoding="utf-8")

    # Ensure no lock file exists.
    lock_file = tmp_path / "integration.aedt.lock"
    if lock_file.exists():
        lock_file.unlink()

    solid_list = ["int_obj1", "int_obj2"]
    result = change_objects_visibility(str(origfile), solid_list)
    assert result is True

    new_content = origfile.read_text(encoding="utf-8")
    expected_view_str = "Drawings[" + str(len(solid_list)) + ": " + str(solid_list).strip("[")
    assert expected_view_str in new_content


def test_integration_change_model_orientation(tmp_path):
    # Create a temporary AEDT file with an OrientationMatrix placeholder.
    content = (
        "$begin 'EditorWindow'\n"
        "Header info\n"
        "OrientationMatrix(old_value)\n"
        "Footer info\n"
        "   $end 'EditorWindow'"
    )
    origfile = tmp_path / "integration.aedt"
    origfile.write_text(content, encoding="utf-8")

    # Ensure no lock file exists.
    lock_file = tmp_path / "integration.aedt.lock"
    if lock_file.exists():
        lock_file.unlink()

    result = change_model_orientation(str(origfile), "+Y")
    assert result is True

    new_content = origfile.read_text(encoding="utf-8")
    # Verify that the OrientationMatrix placeholder was replaced.
    assert "OrientationMatrix(" in new_content and "old_value" not in new_content
