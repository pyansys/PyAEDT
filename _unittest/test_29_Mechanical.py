import os
import shutil

from _unittest.conftest import BasisTest  # Setup paths for module imports
from _unittest.conftest import config  # Setup paths for module imports
from _unittest.conftest import desktop_version  # Setup paths for module imports
from pyaedt import Hfss
from pyaedt import Icepak
from pyaedt import Mechanical

try:
    import pytest
except ImportError:
    import _unittest_ironpython.conf_unittest as pytest

test_project_name = "coax_Mech"


class TestClass(BasisTest, object):
    def setup_class(self):
        BasisTest.my_setup(self)
        self.aedtapp = BasisTest.add_app(self, application=Mechanical, solution_type="Thermal")

    def teardown_class(self):
        BasisTest.my_teardown(self)

    def test_01_save(self):
        test_project = os.path.join(self.local_scratch.path, test_project_name + ".aedt")
        self.aedtapp.save_project(test_project)
        assert os.path.exists(test_project)

    def test_02_create_primitive(self):
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        coax_dimension = 30
        o = self.aedtapp.modeler.create_cylinder(
            self.aedtapp.PLANE.XY, udp, 3, coax_dimension, 0, "MyCylinder", "brass"
        )
        assert isinstance(o.id, int)

    def test_03_assign_convection(self):
        face = self.aedtapp.modeler["MyCylinder"].faces[0].id
        assert self.aedtapp.assign_uniform_convection(face, 3)

    def test_04_assign_temperature(self):
        face = self.aedtapp.modeler["MyCylinder"].faces[1].id
        bound = self.aedtapp.assign_uniform_temperature(face, "35deg")
        assert bound.props["Temperature"] == "35deg"

    def test_05_assign_load(self):
        hfss = Hfss(specified_version=desktop_version)
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        coax_dimension = 30
        hfss.modeler.create_cylinder(self.aedtapp.PLANE.XY, udp, 3, coax_dimension, 0, "MyCylinder", "brass")
        setup = hfss.create_setup()
        freq = "1GHz"
        setup.props["Frequency"] = freq
        assert self.aedtapp.assign_em_losses(
            hfss.design_name,
            hfss.setups[0].name,
            "LastAdaptive",
            freq,
        )

    def test_06a_create_setup(self):
        mysetup = self.aedtapp.create_setup()
        mysetup.props["Solver"] = "Direct"
        assert mysetup.update()

    @pytest.mark.skipif(config["desktopVersion"] < "2021.2", reason="Skipped on versions lower than 2021.2")
    def test_07_assign_thermal_loss(self):
        ipk = Icepak(
            solution_type=self.aedtapp.SOLUTIONS.Icepak.SteadyTemperatureAndFlow, specified_version=desktop_version
        )
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        coax_dimension = 30
        ipk.modeler.create_cylinder(ipk.PLANE.XY, udp, 3, coax_dimension, 0, "MyCylinder", "brass")
        ipk.create_setup()
        self.aedtapp.oproject.InsertDesign("Mechanical", "MechanicalDesign1", "Structural", "")
        self.aedtapp.set_active_design("MechanicalDesign1")
        self.aedtapp.create_setup()
        self.aedtapp.modeler.create_cylinder(self.aedtapp.PLANE.XY, udp, 3, coax_dimension, 0, "MyCylinder", "brass")
        assert self.aedtapp.assign_thermal_map("MyCylinder", ipk.design_name)

    def test_07_assign_mechanical_boundaries(self):
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        coax_dimension = 30
        self.aedtapp.oproject.InsertDesign("Mechanical", "MechanicalDesign2", "Modal", "")
        self.aedtapp.set_active_design("MechanicalDesign2")
        self.aedtapp.modeler.create_cylinder(self.aedtapp.PLANE.XY, udp, 3, coax_dimension, 0, "MyCylinder", "brass")
        self.aedtapp.create_setup()
        assert self.aedtapp.assign_fixed_support(self.aedtapp.modeler["MyCylinder"].faces[0].id)
        assert self.aedtapp.assign_frictionless_support(self.aedtapp.modeler["MyCylinder"].faces[1].id)
        self.aedtapp.oproject.InsertDesign("Mechanical", "MechanicalDesign3", "Thermal", "")
        self.aedtapp.set_active_design("MechanicalDesign3")
        self.aedtapp.modeler.create_cylinder(self.aedtapp.PLANE.XY, udp, 3, coax_dimension, 0, "MyCylinder", "brass")
        assert not self.aedtapp.assign_fixed_support(self.aedtapp.modeler["MyCylinder"].faces[0].id)
        assert not self.aedtapp.assign_frictionless_support(self.aedtapp.modeler["MyCylinder"].faces[0].id)

    def test_08_mesh_settings(self):
        assert self.aedtapp.mesh.initial_mesh_settings
        assert self.aedtapp.mesh.initial_mesh_settings.props

    def test_09_assign_heat_flux(self):
        self.aedtapp.insert_design("Th1", "Thermal")
        self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 3], "box1", "copper")
        b2 = self.aedtapp.modeler.create_box([20, 20, 2], [10, 10, 3], "box2", "copper")
        hf1 = self.aedtapp.assign_heat_flux(["box1"], heat_flux_type="Total Power", value="5W")
        hf2 = self.aedtapp.assign_heat_flux([b2.top_face_x.id], heat_flux_type="Surface Flux", value="25mW_per_m2")
        assert hf1.props["TotalPower"] == "5W"
        assert hf2.props["SurfaceFlux"] == "25mW_per_m2"

    def test_10_assign_heat_generation(self):
        self.aedtapp.insert_design("Th2", "Thermal")
        self.aedtapp.modeler.create_box([40, 40, 2], [10, 10, 3], "box3", "copper")
        hg1 = self.aedtapp.assign_heat_generation(["box3"], value="1W", boundary_name="heatgenBC")
        assert hg1.props["TotalPower"] == "1W"

    def test_11_add_mesh_link(self):
        self.aedtapp.save_project(self.aedtapp.project_file)
        self.aedtapp.set_active_design("MechanicalDesign1")
        assert self.aedtapp.setups[0].add_mesh_link(design_name="MechanicalDesign2")
        meshlink_props = self.aedtapp.setups[0].props["MeshLink"]
        assert meshlink_props["Project"] == "This Project*"
        assert meshlink_props["PathRelativeTo"] == "TargetProject"
        assert meshlink_props["Design"] == "MechanicalDesign2"
        assert meshlink_props["Soln"] == "MySetupAuto : LastAdaptive"
        assert meshlink_props["Params"] == self.aedtapp.available_variations.nominal_w_values_dict
        assert not self.aedtapp.setups[0].add_mesh_link(design_name="")
        assert not self.aedtapp.setups[0].add_mesh_link(
            design_name="MechanicalDesign2", solution_name="Setup_Test : LastAdaptive"
        )
        assert self.aedtapp.setups[0].add_mesh_link(
            design_name="MechanicalDesign2",
            parameters_dict=self.aedtapp.available_variations.nominal_w_values_dict,
        )
        assert self.aedtapp.setups[0].add_mesh_link(
            design_name="MechanicalDesign2", solution_name="MySetupAuto : LastAdaptive"
        )
        example_project = os.path.join(self.local_scratch.path, test_project_name + ".aedt")
        example_project_copy = os.path.join(self.local_scratch.path, test_project_name + "_copy.aedt")
        shutil.copyfile(example_project, example_project_copy)
        assert self.aedtapp.setups[0].add_mesh_link(design_name="MechanicalDesign2", project_name=example_project_copy)
        os.remove(example_project_copy)
