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
import tempfile

from ansys.aedt.core import Hfss
from ansys.aedt.core import Hfss3dLayout
from ansys.aedt.core import Icepak
from ansys.aedt.core import get_pyaedt_app
from ansys.aedt.core.application.aedt_objects import AedtObjects
from ansys.aedt.core.application.design import DesignSettings
from ansys.aedt.core.application.design_solutions import model_names
from ansys.aedt.core.generic.general_methods import is_linux
from ansys.aedt.core.generic.general_methods import settings
from ansys.aedt.core.workflows import customize_automation_tab
import pytest

from tests import TESTS_GENERAL_PATH
from tests.system.general.conftest import config
from tests.system.general.conftest import desktop_version

test_subfolder = "T01"
if config["desktopVersion"] > "2022.2":
    test_project_name = "Coax_HFSS_231"
else:
    test_project_name = "Coax_HFSS"


@pytest.fixture(scope="class")
def aedtapp(add_app):
    app = add_app(test_project_name, subfolder=test_subfolder)
    return app


class TestClass:
    @pytest.fixture(autouse=True)
    def init(self, aedtapp, local_scratch):
        self.aedtapp = aedtapp
        self.local_scratch = local_scratch

    def test_app(self):
        assert self.aedtapp

    def test_01_designname(self):
        # TODO: Remove subsequent dependence on string "myname"
        design_names = ["myname", "design2"]
        self.aedtapp.design_name = design_names[0]  # Change the design name.
        assert self.aedtapp.design_name == design_names[0]
        self.aedtapp.insert_design(design_names[1])  # Insert a new design
        assert self.aedtapp.design_name == design_names[1]
        self.aedtapp.design_name = design_names[0]  # Change current design back.
        assert len(self.aedtapp.design_list) == 2  # Make sure there are still 2 designs.
        assert self.aedtapp.design_list[0] in design_names  # Make sure the name is correct.
        self.aedtapp.delete_design(design_names[1])  # Delete the 2nd design
        assert len(self.aedtapp.design_list) == 1

    def test_01_version_id(self):
        assert self.aedtapp.aedt_version_id

    def test_01_valid_design(self):
        assert self.aedtapp.valid_design

    def test_01_clean_proj_folder(self):
        assert self.aedtapp.clean_proj_folder()

    def test_01_installed_path(self):
        assert self.aedtapp.desktop_class.install_path

    def test_01_desktop_class_path(self):
        assert os.path.exists(self.aedtapp.desktop_class.project_path())
        assert os.path.exists(self.aedtapp.desktop_class.project_path(self.aedtapp.project_name))

        assert len(self.aedtapp.desktop_class.design_list(self.aedtapp.project_name)) == 1
        assert self.aedtapp.desktop_class.design_type() == "HFSS"
        assert self.aedtapp.desktop_class.design_type(self.aedtapp.project_name, self.aedtapp.design_name) == "HFSS"
        assert os.path.exists(self.aedtapp.desktop_class.src_dir)
        assert os.path.exists(self.aedtapp.desktop_class.pyaedt_dir)

    def test_02_copy_project(self):
        assert self.aedtapp.copy_project(self.local_scratch.path, "new_file")
        assert self.aedtapp.copy_project(self.local_scratch.path, test_project_name)

    def test_02_use_causalmaterial(self):
        assert self.aedtapp.change_automatically_use_causal_materials(True)
        assert self.aedtapp.change_automatically_use_causal_materials(False)

    def test_02_design_list(self):
        mylist = self.aedtapp.design_list
        assert len(mylist) == 1

    def test_03_design_type(self):
        assert self.aedtapp.design_type == "HFSS"

    def test_04_projectname(self):
        assert self.aedtapp.project_name == test_project_name

    def test_05_lock(self):
        assert os.path.exists(self.aedtapp.lock_file)

    def test_05_resultsfolder(self):
        assert os.path.exists(self.aedtapp.results_directory)

    def test_05_solution_type(self):
        assert "Modal" in self.aedtapp.solution_type
        self.aedtapp.solution_type = "Terminal"
        assert "Terminal" in self.aedtapp.solution_type
        self.aedtapp.solution_type = "Modal"

    def test_06_libs(self):
        assert os.path.exists(self.aedtapp.personallib)
        assert os.path.exists(self.aedtapp.userlib)
        assert os.path.exists(self.aedtapp.syslib)
        assert os.path.exists(self.aedtapp.temp_directory)
        assert os.path.exists(self.aedtapp.toolkit_directory)
        assert os.path.exists(self.aedtapp.working_directory)

    def test_06a_set_temp_dir(self):
        assert os.path.exists(self.aedtapp.set_temporary_directory(os.path.join(self.local_scratch.path, "temp_dir")))
        assert self.aedtapp.set_temporary_directory(os.path.join(self.local_scratch.path, "temp_dir"))
        self.aedtapp.set_temporary_directory(tempfile.gettempdir())

    def test_08_objects(self):
        print(self.aedtapp.oboundary)
        print(self.aedtapp.oanalysis)
        print(self.aedtapp.odesktop)
        print(self.aedtapp.logger)
        print(self.aedtapp.variable_manager)
        print(self.aedtapp.materials)
        print(self.aedtapp)
        assert self.aedtapp.info

    def test_09_set_objects_deformation(self):
        assert self.aedtapp.modeler.set_objects_deformation(["inner"])

    def test_09_set_objects_temperature(self):
        ambient_temp = 22
        objects = [o for o in self.aedtapp.modeler.solid_names if self.aedtapp.modeler[o].model]
        assert self.aedtapp.modeler.set_objects_temperature(
            objects, ambient_temperature=ambient_temp, create_project_var=True
        )

    def test_10_change_material_override(self):
        assert self.aedtapp.change_material_override(True)
        assert self.aedtapp.change_material_override(False)

    def test_11_change_validation_settings(self):
        assert self.aedtapp.change_validation_settings()
        assert self.aedtapp.change_validation_settings(ignore_unclassified=True, skip_intersections=True)

    def test_12_variables(self):
        self.aedtapp["test"] = "1mm"
        val = self.aedtapp["test"]
        assert val == "1mm"
        del self.aedtapp["test"]
        assert "test" not in self.aedtapp.variable_manager.variables

    def test_13_designs(self):
        with pytest.raises(ValueError):
            self.aedtapp._insert_design(design_name="invalid", design_type="invalid")
        assert self.aedtapp._insert_design(design_name="TestTransient", design_type="HFSS") == "TestTransient"
        self.aedtapp.delete_design("TestTransient")
        self.aedtapp.insert_design("NewDesign")

    def test_14_get_nominal_variation(self):
        assert self.aedtapp.get_nominal_variation() != {} or self.aedtapp.get_nominal_variation() is not None
        assert isinstance(self.aedtapp.get_nominal_variation(), dict)
        assert isinstance(self.aedtapp.get_nominal_variation(with_values=True), dict)
        assert self.aedtapp.get_nominal_variation(with_values=True) != {}

    def test_15a_duplicate_design(self):
        self.aedtapp.duplicate_design("non_valid1", False)
        self.aedtapp.duplicate_design("myduplicateddesign")
        assert "myduplicateddesign" in self.aedtapp.design_list
        self.aedtapp.delete_design("myduplicateddesign", "NewDesign")

    def test_15b_copy_design_from(self):
        origin = os.path.join(self.local_scratch.path, "origin.aedt")
        destin = os.path.join(self.local_scratch.path, "destin.aedt")
        self.aedtapp.save_project(file_name=origin)
        self.aedtapp.duplicate_design("myduplicateddesign")
        self.aedtapp.save_project(file_name=origin, refresh_ids=True)

        self.aedtapp.save_project(file_name=destin)
        new_design = self.aedtapp.copy_design_from(origin, "myduplicateddesign")
        assert new_design in self.aedtapp.design_list

    def test_16_renamedesign(self, add_app, test_project_file):
        prj_file = test_project_file(test_project_name)
        self.aedtapp.load_project(file_name=prj_file, design="myname", close_active=True)
        assert "myname" in [
            design["Name"]
            for design in self.aedtapp.project_properties["AnsoftProject"][model_names[self.aedtapp.design_type]]
        ]
        self.aedtapp.rename_design("mydesign")
        assert "myname" not in [
            design["Name"]
            for design in self.aedtapp.project_properties["AnsoftProject"][model_names[self.aedtapp.design_type]]
        ]
        assert "mydesign" in [
            design["Name"]
            for design in self.aedtapp.project_properties["AnsoftProject"][model_names[self.aedtapp.design_type]]
        ]
        assert self.aedtapp.design_name == "mydesign"

    def test_17_export_proj_var(self):
        self.aedtapp.export_variables_to_csv(os.path.join(self.local_scratch.path, "my_variables.csv"))
        assert os.path.exists(os.path.join(self.local_scratch.path, "my_variables.csv"))

    def test_19_create_design_dataset(self):
        x = [1, 100]
        y = [1000, 980]
        ds1 = self.aedtapp.create_dataset1d_design("Test_DataSet", x, y)
        assert ds1.name == "Test_DataSet"
        assert ds1.add_point(10, 999)
        assert ds1.add_point(12, 1500)
        assert ds1.remove_point_from_x(100)
        assert self.aedtapp.dataset_exists("Test_DataSet", is_project_dataset=False)
        assert not self.aedtapp.dataset_exists("Test_DataSet", is_project_dataset=True)

    def test_19_create_project_dataset(self):
        x = [1, 100]
        y = [1000, 980]
        ds2 = self.aedtapp.create_dataset1d_project("Test_DataSet", x, y)
        assert ds2.name == "$Test_DataSet"
        assert self.aedtapp.dataset_exists("Test_DataSet", is_project_dataset=True)
        assert ds2.delete()
        assert not self.aedtapp.dataset_exists("Test_DataSet", is_project_dataset=True)
        ds3 = self.aedtapp.create_dataset1d_project("Test_DataSet2", x, y, sort=False)
        assert ds3.name == "$Test_DataSet2"

    def test_19_create_3dproject_dataset(self):
        x = [1, 100]
        y = [1000, 980]
        z = [800, 200]
        v = [10, 20]
        vunits = "cel"
        ds3 = self.aedtapp.create_dataset3d("Test_DataSet3D", x, y, z, v, v_unit=vunits)
        assert ds3.name == "$Test_DataSet3D"
        ds3.sort = False
        ds3.v = [50, 200]
        assert ds3.update()
        ds30 = self.aedtapp.create_dataset3d("Test_DataSet3D1", x, y, z, v, v_unit=vunits, is_project_dataset=False)
        assert ds30.name == "$Test_DataSet3D1"
        ds31 = self.aedtapp.create_dataset3d("$Test_DataSet3D2", x, y, z, v, v_unit=vunits, is_project_dataset=False)
        assert ds31.name == "$Test_DataSet3D2"

    def test_19_edit_existing_dataset(self):
        ds = self.aedtapp.project_datasets["$AluminumconductivityTH0"]
        xl = len(ds.x)
        assert ds.add_point(300, 0.8)
        assert len(ds.x) == xl + 1

    def test_19_import_dataset1d(self):
        filename = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "ds_1d.tab")
        ds4 = self.aedtapp.import_dataset1d(filename)
        assert ds4.name == "$ds_1d"
        ds5 = self.aedtapp.import_dataset1d(filename, name="dataset_test", is_project_dataset=False)
        assert ds5.name == "dataset_test"
        ds6 = self.aedtapp.import_dataset1d(filename, name="$dataset_test2")
        assert ds6.name == "$dataset_test2"
        ds7 = self.aedtapp.import_dataset1d(filename)
        assert not ds7
        assert ds4.delete()
        assert self.aedtapp.import_dataset1d(filename)
        assert ds5.delete()

    def test_19a_import_dataset3d(self):
        filename = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "Dataset_3D.tab")
        ds8 = self.aedtapp.import_dataset3d(filename)
        assert ds8.name == "$Dataset_3D"
        filename = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "Dataset_3D.csv")
        ds8 = self.aedtapp.import_dataset3d(filename, name="dataset_csv")
        assert ds8.name == "$dataset_csv"
        assert ds8.delete()
        ds10 = self.aedtapp.import_dataset3d(filename, name="$dataset_test")
        assert ds10.zunit == "mm"
        filename = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "Dataset_3D.csv")
        ds8 = self.aedtapp.import_dataset3d(filename, name="dataset_csv", encoding="utf-8-sig")
        assert ds8.name == "$dataset_csv"

    def test_19b_import_dataset3d_xlsx(self):
        filename = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "Dataset_3D.xlsx")
        ds9 = self.aedtapp.import_dataset3d(filename, name="myExcel")
        assert ds9.name == "$myExcel"

    def test_20_get_3dComponents_properties(self):
        assert len(self.aedtapp.components3d) > 0
        props = self.aedtapp.get_components3d_vars("Dipole_Antenna_DM")
        assert len(props) == 3

    @pytest.mark.skipif(is_linux, reason="Not needed in Linux.")
    def test_21_generate_temp_project_directory(self):
        proj_dir1 = self.aedtapp.generate_temp_project_directory("Example")
        assert os.path.exists(proj_dir1)
        proj_dir2 = self.aedtapp.generate_temp_project_directory("")
        assert os.path.exists(proj_dir2)
        proj_dir4 = self.aedtapp.generate_temp_project_directory(34)
        assert not proj_dir4

    def test_22_export_aedtz(self):
        aedtz_proj = os.path.join(self.local_scratch.path, "test.aedtz")
        assert self.aedtapp.archive_project(aedtz_proj)
        assert os.path.exists(aedtz_proj)

    def test_23_autosave(self):
        assert self.aedtapp.autosave_enable()
        assert self.aedtapp.autosave_disable()

    def test_24_change_type(self):
        assert self.aedtapp.set_license_type("Pack")
        assert self.aedtapp.set_license_type("Pool")

    def test_25_change_registry_from_file(self):
        assert self.aedtapp.set_registry_from_file(
            os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "Test.acf")
        )

    def test_26_odefinition_manager(self):
        assert self.aedtapp.odefinition_manager
        assert self.aedtapp.omaterial_manager

    def test_27_odesktop(self):
        assert str(type(self.aedtapp.odesktop)) in [
            "<class 'win32com.client.CDispatch'>",
            "<class 'PyDesktopPlugin.AedtObjWrapper'>",
            "<class 'ansys.aedt.core.generic.grpc_plugin.AedtObjWrapper'>",
            "<class 'ansys.aedt.core.generic.grpc_plugin_dll_class.AedtObjWrapper'>",
        ]

    def test_28_get_pyaedt_app(self):
        app = get_pyaedt_app(self.aedtapp.project_name, self.aedtapp.design_name)
        assert app.design_type == "HFSS"

    def test_29_change_registry_key(self, desktop):
        assert not desktop.change_registry_key("test_key_string", "test_string")
        assert not desktop.change_registry_key("test_key_int", 2)
        assert not desktop.change_registry_key("test_key", 2.0)

    def test_30_object_oriented(self):
        self.aedtapp["my_oo_variable"] = "15mm"
        assert self.aedtapp.get_oo_name(self.aedtapp.oproject, "Variables")
        assert self.aedtapp.get_oo_name(self.aedtapp.odesign, "Variables")
        assert not self.aedtapp.get_oo_name(self.aedtapp.odesign, "Variables1")
        assert self.aedtapp.get_oo_object(self.aedtapp.oproject, "Variables")
        assert not self.aedtapp.get_oo_object(self.aedtapp.oproject, "Variables1")
        assert self.aedtapp.get_oo_properties(self.aedtapp.oproject, "Variables\\$height")
        assert self.aedtapp.get_oo_property_value(self.aedtapp.oproject, "Variables\\$height", "Value") == "10mm"

    def test_31_make_hidden_variable(self):
        self.aedtapp["my_hidden_variable"] = "15mm"
        assert self.aedtapp.hidden_variable("my_hidden_variable")
        self.aedtapp.hidden_variable("my_hidden_variable", False)
        assert self.aedtapp.hidden_variable(["my_oo_variable", "$dim", "my_hidden_variable"])
        self.aedtapp.hidden_variable(["my_oo_variable", "$dim"], False)

    def test_32_make_read_only_variable(self):
        self.aedtapp["my_read_only_variable"] = "15mm"
        assert self.aedtapp.read_only_variable("my_read_only_variable")

    def test_33_aedt_object(self):
        aedt_obj = AedtObjects()
        assert aedt_obj._odesign
        assert aedt_obj._oproject
        aedt_obj = AedtObjects(self.aedtapp._desktop_class, self.aedtapp.oproject, self.aedtapp.odesign)
        assert aedt_obj._odesign == self.aedtapp.odesign

    def test_34_force_project_path_disable(self):
        settings.force_error_on_missing_project = True
        assert settings.force_error_on_missing_project
        e = None
        exception_raised = False
        try:
            h = Hfss("c:/dummy/test.aedt", version=desktop_version)
        except Exception as e:
            exception_raised = True
            assert e.args[0] == "Project doesn't exist. Check it and retry."
        assert exception_raised
        settings.force_error_on_missing_project = False

    def test_35_get_app(self, desktop):
        d = desktop
        assert d[[0, 0]]
        assert not d[[test_project_name, "myname"]]
        assert d[[0, "mydesign"]]
        assert d[[test_project_name, 2]]
        assert not d[[test_project_name, 5]]
        assert not d[[1, 0]]
        assert not d[[1, 0, 3]]
        self.aedtapp.create_new_project("Test")
        assert d[[1, 0]]
        assert "Test" in d[[1, 0]].project_name

    def test_36_test_load(self, add_app):
        file_name = os.path.join(self.local_scratch.path, "test_36.aedt")
        hfss = add_app(project_name=file_name, just_open=True)
        hfss.save_project()
        assert hfss
        h3d = add_app(project_name=file_name, application=Hfss3dLayout, just_open=True)
        assert h3d
        h3d = add_app(project_name=file_name, application=Hfss3dLayout, just_open=True)
        assert h3d
        file_name2 = os.path.join(self.local_scratch.path, "test_36_2.aedt")
        file_name2_lock = os.path.join(self.local_scratch.path, "test_36_2.aedt.lock")
        with open(file_name2, "w") as f:
            f.write(" ")
        with open(file_name2_lock, "w") as f:
            f.write(" ")
        try:
            hfss = Hfss(project=file_name2, version=desktop_version)
        except Exception:
            assert True
        try:
            os.makedirs(os.path.join(self.local_scratch.path, "test_36_2.aedb"))
            file_name3 = os.path.join(self.local_scratch.path, "test_36_2.aedb", "edb.def")
            with open(file_name3, "w") as f:
                f.write(" ")
            hfss = Hfss3dLayout(project=file_name3, version=desktop_version)
        except Exception:
            assert True

    def test_37_add_custom_toolkit(self, desktop):
        assert customize_automation_tab.available_toolkits()

    def test_38_toolkit(self, desktop):
        file = os.path.join(self.local_scratch.path, "test.py")
        with open(file, "w") as f:
            f.write("import ansys.aedt.core\n")
        assert customize_automation_tab.add_script_to_menu(name="test_toolkit", script_file=file)
        assert customize_automation_tab.remove_script_from_menu(
            desktop_object=self.aedtapp.desktop_class, name="test_toolkit"
        )
        assert customize_automation_tab.add_script_to_menu(
            name="test_toolkit",
            script_file=file,
            personal_lib=self.aedtapp.desktop_class.personallib,
            aedt_version=self.aedtapp.desktop_class.aedt_version_id,
        )
        assert customize_automation_tab.remove_script_from_menu(
            desktop_object=self.aedtapp.desktop_class, name="test_toolkit"
        )

    def test_39_load_project(self, desktop):
        new_project = os.path.join(self.local_scratch.path, "new.aedt")
        self.aedtapp.save_project(file_name=new_project)
        self.aedtapp.close_project(name="new")
        aedtapp = desktop.load_project(new_project)
        assert aedtapp

    def test_40_get_design_settings(self, add_app):
        ipk = add_app(application=Icepak)
        design_settings_dict = ipk.design_settings

        assert isinstance(design_settings_dict, DesignSettings)
        assert "AmbTemp" in design_settings_dict
        assert "AmbRadTemp" in design_settings_dict
        assert "GravityVec" in design_settings_dict
        assert "GravityDir" in design_settings_dict

    def test_41_desktop_reference_counting(self, desktop):
        num_references = desktop._connected_app_instances
        with Hfss() as hfss:
            assert hfss
            assert desktop._connected_app_instances == num_references + 1
            hfss.set_active_design(hfss.design_name)
            assert desktop._connected_app_instances == num_references + 1
        assert desktop._connected_app_instances == num_references

    def test_42_save_project_with_file_name(self):
        # Save into path with existing parent dir
        self.aedtapp.create_new_project("Test")
        new_project = os.path.join(self.local_scratch.path, "new.aedt")
        assert os.path.exists(self.local_scratch.path)
        self.aedtapp.save_project(file_name=new_project)
        assert os.path.isfile(new_project)

        # Save into path with non-existing parent dir
        new_parent_dir = os.path.join(self.local_scratch.path, "new_dir")
        new_project = os.path.join(new_parent_dir, "new_2.aedt")
        assert not os.path.exists(new_parent_dir)
        self.aedtapp.save_project(file_name=new_project)
        assert os.path.isfile(new_project)

    def test_43_edit_notes(self):
        assert self.aedtapp.edit_notes("this a test")
        assert not self.aedtapp.edit_notes(1)
