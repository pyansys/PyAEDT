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

"""This module contains the `Mesh` class."""

from __future__ import absolute_import  # noreorder

import os
import shutil

from ansys.aedt.core.application.design_solutions import model_names
from ansys.aedt.core.generic.data_handlers import _dict2arg
from ansys.aedt.core.generic.errors import MethodNotSupportedError
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import settings
from ansys.aedt.core.generic.load_aedt_file import load_keyword_in_aedt_file
from ansys.aedt.core.generic.numbers import _units_assignment
from ansys.aedt.core.modeler.cad.elements_3d import BinaryTreeNode
from ansys.aedt.core.modeler.cad.elements_3d import EdgePrimitive
from ansys.aedt.core.modeler.cad.elements_3d import FacePrimitive
from ansys.aedt.core.modeler.cad.elements_3d import VertexPrimitive

meshers = {
    "HFSS": "MeshSetup",
    "Icepak": "MeshRegion",
    "HFSS3DLayout": "MeshSetup",
    "Maxwell 2D": "MeshSetup",
    "Maxwell 3D": "MeshSetup",
    "Q3D Extractor": "MeshSetup",
    "Mechanical": "MeshSetup",
    "2D Extractor": "MeshSetup",
}

mesh_props = {
    "CurvedSurfaceApproxChoice": "Curved Mesh Approximation Type",
    "SliderMeshSettings": "Curved Surface Mesh Resolution",
    "SurfDevChoice": "Surface Deviation Choice",
    "SurfDev": "Surface Deviation",
    "NormalDevChoice": "Normal Deviation Choice",
    "NormalDev": "Normal Deviation",
    "AspectRatioChoice": "Aspect Ratio Choice",
    "AspectRatio": "Aspect Ratio",
    "UseAutoLength": "Use Auto Simplify",
    "DefeatureLength": "Model Resolution Length",
    "SurfaceRepPriority": "Surface Representation Priority for TAU",
    "RestrictLength": "Restrict Length",
    "MaxLength": "Max Length",
    "RestrictElem": "Restrict Max Elems",
    "SkinDepth": "Skin Depth",
    "NumLayers": "Num Layers",
    "SurfTriMaxLength": "Max Elem Length",
    "NumMaxElem": "Max Elems",
    "Apply": "Apply Curvilinear Elements",
    "DisableForFacetedSurfaces": "Disable for Faceted Surface",
    "RestrictMaxElemLength": "Restrict Max Element Length",
    "MaxElemLength": "Max Element Length",
    "RestrictLayersNum": "Restrict Layers Number",
    "LayersNum": "Number of layers",
}


class MeshProps(dict):
    """AEDT Mesh Component Internal Parameters."""

    def __setitem__(self, key, value):
        value = _units_assignment(value)
        dict.__setitem__(self, key, value)
        if self._pyaedt_mesh.auto_update:
            if key in ["Edges", "Faces", "Objects"]:
                res = self._pyaedt_mesh.update_assignment()
            else:
                res = self._pyaedt_mesh.update(key, value)
            if not res:
                self._pyaedt_mesh._app.logger.warning("Update of %s Failed. Check needed arguments", key)

    def __init__(self, mesh_object, props):
        dict.__init__(self)
        if props:
            for key, value in props.items():
                if isinstance(value, (dict, dict)):
                    dict.__setitem__(self, key, MeshProps(mesh_object, value))
                else:
                    dict.__setitem__(self, key, value)
        self._pyaedt_mesh = mesh_object

    def _setitem_without_update(self, key, value):
        dict.__setitem__(self, key, value)


class MeshOperation(BinaryTreeNode):
    """MeshOperation class.

    Parameters
    ----------
    mesh : class:`ansys.aedt.core.modules.mesh.Mesh or :class:`ansys.aedt.core.modules.mesh_icepak.MeshIcepak`

    """

    def __init__(self, mesh, name, props, meshoptype):
        self._mesh = mesh
        self._app = self._mesh._app
        self._legacy_props = None
        if props is not None:
            self._legacy_props = MeshProps(self, props)
        self._type = meshoptype
        self._name = name
        self.auto_update = True
        self._initialize_tree_node()

    @property
    def _child_object(self):
        """Object-oriented properties.

        Returns
        -------
        class:`ansys.aedt.core.modeler.cad.elements_3d.BinaryTreeNode`

        """
        child_object = None
        design_childs = self._app.get_oo_name(self._app.odesign)

        if "Mesh" in design_childs:
            cc = self._app.get_oo_object(self._app.odesign, "Mesh")
            cc_names = self._app.get_oo_name(cc)
            if self._name in cc_names:
                child_object = cc.GetChildObject(self._name)
        return child_object

    @property
    def type(self):
        if not self._type:
            self._type = self.props.get("Type", None)
        return self._type

    @property
    def props(self):
        """Properties of the mesh operation."""
        if not self._legacy_props:
            props = {}
            for k, v in self.properties.items():
                props[k] = v
            if "Assignment" in props:
                assignment = props["Assignment"]
                if "Face_" in assignment:
                    props["Faces"] = [
                        int(i.replace("Face_", "")) for i in assignment.split("(")[1].split(")")[0].split(",")
                    ]
                elif "Edge_" in assignment:
                    props["Edges"] = [
                        int(i.replace("Edge_", "")) for i in assignment.split("(")[1].split(")")[0].split(",")
                    ]
                else:
                    props["Objects"] = assignment
            else:
                props["Objects"] = []
                props["Faces"] = []
                props["Edges"] = []
                assigned_id = self._mesh.omeshmodule.GetMeshOpAssignment(self.name)
                for comp_id in assigned_id:
                    if int(comp_id) in self._app.modeler.objects.keys():
                        props["Objects"].append(self._app.oeditor.GetObjectNameByID(comp_id))
                        continue
                    for comp in self._app.modeler.object_list:
                        faces = comp.faces
                        face_ids = [face.id for face in faces]
                        if int(comp_id) in face_ids:
                            props["Faces"].append(int(comp_id))
                            continue
                        edges = comp.edges
                        edge_ids = [edge.id for edge in edges]
                        if int(comp_id) in edge_ids:
                            props["Edges"].append(int(comp_id))
                            continue
            self._legacy_props = MeshProps(self, props)
        return self._legacy_props

    @pyaedt_function_handler()
    def _get_args(self):
        """Retrieve arguments."""
        props = self.props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg

    @property
    def name(self):
        """Name of the mesh operation.

        Returns
        -------
        str
           Name of the mesh operation.

        """
        if self._child_object:
            self._name = str(self.properties["Name"])
        return self._name

    @name.setter
    def name(self, meshop_name):
        if self._child_object:
            try:
                self.properties["Name"] = meshop_name
            except KeyError:
                self._mesh.logger.error("Name %s already assigned in the design", meshop_name)

    @pyaedt_function_handler()
    def create(self):
        """Create a mesh.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.type == "SurfApproxBased":
            self._mesh.omeshmodule.AssignTrueSurfOp(self._get_args())
        elif self.type == "DefeatureBased":
            self._mesh.omeshmodule.AssignModelResolutionOp(self._get_args())
        elif self.type == "SurfaceRepPriority":
            self._mesh.omeshmodule.AssignSurfPriorityForTauOp(self._get_args())
        elif self.type == "LengthBased":
            self._mesh.omeshmodule.AssignLengthOp(self._get_args())
        elif self.type == "SkinDepthBased":
            self._mesh.omeshmodule.AssignSkinDepthOp(self._get_args())
        elif self.type == "Curvilinear":
            self._mesh.omeshmodule.AssignApplyCurvlinearElementsOp(self._get_args())
        elif self.type == "RotationalLayerMesh":
            self._mesh.omeshmodule.AssignRotationalLayerOp(self._get_args())
        elif self.type == "EdgeCutLayerMesh":
            self._mesh.omeshmodule.AssignEdgeCutLayerOp(self._get_args())
        elif self.type == "DensityControlBased":
            self._mesh.omeshmodule.AssignDensityControlOp(self._get_args())
        elif self.type == "Icepak":
            self._mesh.omeshmodule.AssignMeshOperation(self._get_args())
        elif self.type == "CurvatureExtraction":
            self._mesh.omeshmodule.AssignCurvatureExtractionOp(self._get_args())
        elif self.type == "CylindricalGap":
            self._mesh.omeshmodule.AssignCylindricalGapOp(self._get_args())
        else:
            return False
        return self._initialize_tree_node()

    @pyaedt_function_handler()
    def update(self, key_name=None, value=None):
        """Update the mesh.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.EditTrueSurfOp
        >>> oModule.EditModelResolutionOp
        >>> oModule.EditSurfPriorityForTauOp
        >>> oModule.EditLengthOp
        >>> oModule.EditApplyCurvlinearElementsOp
        >>> oModule.EditRotationalLayerOp
        >>> oModule.EditDensityControlOp
        >>> oModule.EditMeshOperation
        >>> oModule.EditSBRCurvatureExtractionOp
        """
        mesh_names = self._mesh._app.odesign.GetChildObject("Mesh").GetChildNames()
        if key_name and settings.aedt_version > "2022.2" and self.name in mesh_names:
            try:
                mesh_obj = self._mesh._app.odesign.GetChildObject("Mesh").GetChildObject(self.name)
                if key_name in mesh_props.keys():
                    if key_name == "SurfaceRepPriority":
                        value = "Normal" if value == 0 else "High"
                    key_name = mesh_props[key_name]
                mesh_obj.SetPropValue(key_name, value)
                return True
            except Exception:
                self._app.logger.info("Failed to use Child Object. Trying with legacy update.")

        if self.type == "SurfApproxBased":
            self._mesh.omeshmodule.EditTrueSurfOp(self.name, self._get_args())
        elif self.type == "DefeatureBased":
            self._mesh.omeshmodule.EditModelResolutionOp(self.name, self._get_args())
        elif self.type == "SurfaceRepPriority":
            self._mesh.omeshmodule.EditSurfPriorityForTauOp(self.name, self._get_args())
        elif self.type == "LengthBased":
            self._mesh.omeshmodule.EditLengthOp(self.name, self._get_args())
        elif self.type == "SkinDepthBased":
            self._mesh.omeshmodule.EditSkinDepthOp(self.name, self._get_args())
        elif self.type == "Curvilinear":
            self._mesh.omeshmodule.EditApplyCurvlinearElementsOp(self.name, self._get_args())
        elif self.type == "RotationalLayerMesh":
            self._mesh.omeshmodule.EditRotationalLayerOp(self.name, self._get_args())
        elif self.type == "DensityControlBased":
            self._mesh.omeshmodule.EditDensityControlOp(self.name, self._get_args())
        elif self.type == "Icepak":
            self._mesh.omeshmodule.EditMeshOperation(self.name, self._get_args())
        elif self.type == "CurvatureExtraction":
            self._mesh.omeshmodule.EditSBRCurvatureExtractionOp(self.name, self._get_args())
        elif self.type in ["InitialMeshSettings", "MeshSettings"]:
            self._mesh.omeshmodule.InitialMeshSettings(self._get_args())
        elif self.type == "CylindricalGap":
            self._mesh.omeshmodule.EditCylindricalGapOp(self.name, self._get_args())
        else:
            return False
        return True

    @pyaedt_function_handler()
    def update_assignment(self):
        """Update the boundary assignment.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """

        out = []

        if "Faces" in self.props:
            faces = self.props["Faces"]
            faces_out = []
            if not isinstance(faces, list):
                faces = [faces]
            for f in faces:
                if isinstance(f, (EdgePrimitive, FacePrimitive, VertexPrimitive)):
                    faces_out.append(f.id)
                else:
                    faces_out.append(f)
            out += ["Faces:=", faces_out]

        if "Objects" in self.props:
            pr = []
            for el in self.props["Objects"]:
                try:
                    pr.append(self._app.modeler[el].name)
                except (KeyError, AttributeError):
                    self.logger.debug("An error occurred while updating the boundary assignment.")  # pragma: no cover
            out += ["Objects:=", pr]

        if len(out) == 1:
            return False

        self._app.omeshmodule.ReassignOp(self.name, out)

        return True

    @pyaedt_function_handler()
    def _change_property(self, name, arg):
        """Update properties of the mesh operation.

        Parameters
        ----------
        name : str
            Name of the mesh operation.
        arg : list
            List of the properties to update. For example,
            ``["NAME:ChangedProps", ["NAME:Max Length", "Value:=", "2mm"]]``.

        Returns
        -------
        list
            List of changed properties of the mesh operation.

        """
        arguments = ["NAME:AllTabs", ["NAME:MeshSetupTab", ["NAME:PropServers", f"MeshSetup:{name}"], arg]]
        self._mesh._app.odesign.ChangeProperty(arguments)

    @pyaedt_function_handler()
    def delete(self):
        """Delete the mesh.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.DeleteOp
        """
        self._mesh.omeshmodule.DeleteOp([self.name])
        for el in self._mesh.meshoperations[:]:
            if el.name == self.name:
                self._mesh.meshoperations.remove(el)
        return True

    @pyaedt_function_handler()
    def _initialize_tree_node(self):
        if self._child_object:
            BinaryTreeNode.__init__(self, self._name, self._child_object, False, app=self._app)
            return True
        return False


class Mesh(object):
    """Manages AEDT mesh functions for 2D and 3D solvers (HFSS, Maxwell, and Q3D).

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_3d.FieldAnalysis3D`

    Examples
    --------
    Basic usage demonstrated with an HFSS design:

    >>> from ansys.aedt.core import Hfss
    >>> hfss = Hfss()
    >>> cylinder = hfss.modeler.create_cylinder(0,[0, 0, 0],3,20,0)
    >>> model_resolution = hfss.mesh.assign_model_resolution(cylinder,1e-4,"ModelRes1")
    """

    def __init__(self, app):
        app.logger.reset_timer()
        self._app = app
        self._odesign = self._app.odesign
        self.logger = self._app.logger
        self.id = 0
        self._meshoperations = None
        self._globalmesh = None
        app.logger.info_timer("Mesh class has been initialized!")

    @property
    def _modeler(self):
        return self._app.modeler

    @pyaedt_function_handler()
    def __getitem__(self, part_id):
        """Get the object ``Mesh`` for a given mesh operation name.

        Parameters
        ----------
        part_id : str
            Mesh operation name.

        Returns
        -------
        :class:`ansys.aedt.core.mesh.meshoperations`
            Returns None if the part ID or the object name is not found.

        Examples
        --------
        Basic usage demonstrated with an HFSS design:

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> cylinder = hfss.modeler.create_cylinder(0,[0, 0, 0],3,20,0)
        >>> mr1 = hfss.mesh.assign_model_resolution(cylinder,1e-4,"ModelRes1")
        >>> mr2 = hfss.mesh[mr1.name]
        """

        if part_id in self.meshoperation_names:
            mesh_op_selected = [mesh_op for mesh_op in self.meshoperations if mesh_op.name == part_id]
            return mesh_op_selected[0]
        return None

    @property
    def meshoperations(self):
        """Return the available mesh operations.

        Returns
        -------
        list[:class:`ansys.aedt.core.modules.mesh.MeshOperation`]
            List of mesh operation object.

        Examples
        --------
        Basic usage demonstrated with an HFSS design:

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> o = hfss.modeler.create_cylinder(0,[0, 0, 0],3,20,0)
        >>> mr1 = hfss.mesh.assign_model_resolution(o,1e-4,"ModelRes1")
        >>> mesh_operations_list = hfss.mesh.meshoperations
        """
        if self._meshoperations is None:
            self._meshoperations = self._get_design_mesh_operations()
        return self._meshoperations

    @pyaedt_function_handler()
    def _refresh_mesh_operations(self):
        """Refresh all mesh operations."""

        self._meshoperations = self._get_design_mesh_operations()
        return len(self.meshoperations)

    @property
    def meshoperation_names(self):
        """Return the available mesh operation names.

        Returns
        -------
        List
            List of mesh operation names.

        Examples
        --------
        Basic usage demonstrated with an HFSS design:

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> o = hfss.modeler.create_cylinder(0,[0, 0, 0],3,20,0)
        >>> mr1 = hfss.mesh.assign_model_resolution(o,1e-4,"ModelRes1")
        >>> mr2 = hfss.mesh.assign_model_resolution(o,1e-2,"ModelRes2")
        >>> mesh_operations_names = hfss.mesh.meshoperation_names
        """
        if self._app._is_object_oriented_enabled():
            return list(self._app.odesign.GetChildObject("Mesh").GetChildNames())
        return []

    @property
    def initial_mesh_settings(self):
        """Return the global mesh object.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.InitialMeshSettings
        """
        if not self._globalmesh:
            self._globalmesh = self._get_design_global_mesh()
        return self._globalmesh

    @property
    def omeshmodule(self):
        """Aedt Mesh Module.

        References
        ----------
        >>> oDesign.GetModule("MeshSetup")
        """
        return self._app.omeshmodule

    @pyaedt_function_handler()
    def _get_design_global_mesh(self):
        """ """
        props = None
        try:
            props = self._app.design_properties["MeshSetup"]["MeshSettings"]
        except Exception:
            temp_name = generate_unique_name("temp_prj")
            temp_proj = os.path.join(self._app.working_directory, temp_name + ".aedt")
            oproject_target = self._app.odesktop.NewProject(temp_name)
            if self._app.solution_type == "Modal":
                sol = "HFSS Modal Network"
            elif self._app.solution_type == "Terminal":
                sol = "HFSS Terminal Network"
            else:
                sol = self._app.solution_type
            oproject_target.InsertDesign(self._app.design_type, temp_name, sol, "")
            oproject_target.SaveAs(temp_proj, True)
            self._app.odesktop.CloseProject(temp_name)
            # _project_dictionary = load_entire_aedt_file(temp_proj)
            _project_dictionary = load_keyword_in_aedt_file(temp_proj, "AnsoftProject")
            try:
                props = _project_dictionary["AnsoftProject"][model_names[self._app.design_type]]["MeshSetup"][
                    "MeshSettings"
                ]
            except Exception:
                self.logger.debug("An error occurred while accessing design global mesh.")  # pragma: no cover
            if os.path.exists(temp_proj):
                os.remove(temp_proj)
            if os.path.exists(temp_proj + "results"):
                shutil.rmtree(temp_proj + "results", True)
        if props:
            bound = MeshOperation(self, "MeshSettings", props, "InitialMeshSettings")
            return bound
        return {}

    @pyaedt_function_handler()
    def _get_design_mesh_operations(self):
        """ """
        meshops = []
        for ds in self.meshoperation_names:
            meshops.append(MeshOperation(self, ds, {}, ""))
        return meshops

    @pyaedt_function_handler(names="assignment", meshop_name="name")
    def assign_surface_mesh(self, assignment, level, name=None):
        """Assign a surface mesh level to one or more objects.

        Parameters
        ----------
        assignment : list
            One or more names of the objects.
        level : int
            Level of the surface mesh. Options are ``1`` through ``10``
        name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.AssignTrueSurfOp

        Examples
        --------
        Basic usage demonstrated with an HFSS design:

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> o = hfss.modeler.create_cylinder(0,[0, 0, 0],3,20,0)
        >>> surface = hfss.mesh.assign_surface_mesh(o.id,3,"Surface")
        """
        assignment = self._modeler.convert_to_selections(assignment, True)
        if name:
            for m in self.meshoperations:
                if name == m.name:
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("SurfApprox")
        self.logger.info("Assigning Mesh Level " + str(level) + " to " + str(assignment))
        assignment = self._app.modeler.convert_to_selections(assignment, True)

        if isinstance(assignment[0], int):
            seltype = "Faces"
        else:
            seltype = "Objects"
        props = dict(
            {
                "Type": "SurfApproxBased",
                "CurvedSurfaceApproxChoice": "UseSlider",
                seltype: assignment,
                "SliderMeshSettings": level,
            }
        )
        mop = MeshOperation(self, name, props, "SurfApproxBased")
        mop.create()
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler(names="assignment", surf_dev="surface_deviation", meshop_name="name")
    def assign_surface_mesh_manual(
        self, assignment, surface_deviation=None, normal_dev=None, aspect_ratio=None, name=None
    ):
        """Assign a surface mesh to a list of faces.

        Parameters
        ----------
        assignment : list or str or :class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`
            List of faces to apply the surface mesh to.
        surface_deviation : float or str, optional
            Surface deviation. The default is ``None``. You can specify a float value, a number with units, or `"inf"`.
        normal_dev : float or str, optional
            Normal deviation. The default is ``None``.
        aspect_ratio : int, optional
            Aspect ratio. The default is ``None``.
        name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.AssignTrueSurfOp

        Examples
        --------
        Basic usage demonstrated with an HFSS design:

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> o = hfss.modeler.create_cylinder(0,[0, 0, 0],3,20,0)
        >>> surface = hfss.mesh.assign_surface_mesh_manual(o.id,1e-6,aspect_ratio=3,name="Surface_Manual")
        """
        assignment = self._modeler.convert_to_selections(assignment, True)
        if name:
            for m in self.meshoperations:
                if name == m.name:
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("ModelResolution")

        surf_dev_enable = 2
        normal_dev_enable = 2
        aspect_ratio_enable = 2

        if not surface_deviation:
            surf_dev_enable = 0
            surface_deviation = "0.0001mm"
        elif surface_deviation == "inf":
            surf_dev_enable = 1
        if not normal_dev:
            normal_dev_enable = 1
            normal_dev = "1"

        if not aspect_ratio:
            aspect_ratio_enable = 1
            aspect_ratio = "10"

        props = dict(
            {
                "Type": "SurfApproxBased",
                "Objects": assignment,
                "CurvedSurfaceApproxChoice": "ManualSettings",
                "SurfDevChoice": surf_dev_enable,
                "SurfDev": surface_deviation,
                "NormalDevChoice": normal_dev_enable,
                "NormalDev": normal_dev,
                "AspectRatioChoice": aspect_ratio_enable,
                "AspectRatio": aspect_ratio,
            }
        )

        mop = MeshOperation(self, name, props, "SurfApproxBased")
        mop.create()
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler(names="assignment", meshop_name="name")
    def assign_model_resolution(self, assignment, defeature_length=None, name=None):
        """Assign the model resolution.

        Parameters
        ----------
        assignment : list
            List of objects to defeature.
        defeature_length : float, optional
            Defeaturing length in millimeters. The default is ``None``, in which case
            automatic defeaturing is used.
        name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.AssignModelResolutionOp

        Examples
        --------
        Basic usage demonstrated with an HFSS design:

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> o = hfss.modeler.create_cylinder(0,[0, 0, 0],3,20,0)
        >>> surface = hfss.mesh.assign_model_resolution(o,1e-4,"ModelRes1")
        """
        assignment = self._modeler.convert_to_selections(assignment, True)
        if name:
            for m in self.meshoperations:
                if name == m.name:
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("ModelResolution")
        for name in assignment:
            if isinstance(name, int):
                self.logger.error("Mesh Operation Applies to Objects only")
                return False
        if defeature_length is None:
            props = dict({"Objects": assignment, "UseAutoLength": True})
        else:
            props = dict(
                {
                    "Type": "DefeatureBased",
                    "Objects": assignment,
                    "UseAutoLength": False,
                    "DefeatureLength": str(defeature_length) + "mm",
                }
            )

        mop = MeshOperation(self, name, props, "DefeatureBased")
        mop.create()
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler(
        usedynamicsurface="dynamic_surface",
        useflexmesh="flex_mesh",
        applycurvilinear="curvilinear",
        usefallback="fallback",
        usephi="phi",
        automodelresolution="auto_model_resolution",
        modelresolutionlength="model_resolution_length",
    )
    def assign_initial_mesh_from_slider(
        self,
        level=5,
        method="Auto",
        dynamic_surface=True,
        flex_mesh=False,
        curvilinear=False,
        fallback=True,
        phi=True,
        auto_model_resolution=True,
        model_resolution_length="0.0001mm",
    ):
        """Assign a surface mesh level to an object.

        Parameters
        ----------
        level : int, optional
            Level of the surface mesh. Options are ``1`` through ``10``. The default is ``5``.
        method : str, optional
            Meshing method. Options are ``"Auto"``, ``"AnsoftTAU"``, and ``"AnsoftClassic"``
            The default is ``"Auto"``.
        dynamic_surface : bool, optional
            Whether to use dynamic surface resolution. The default is ``True``.
        flex_mesh : bool, optional
            Whether to use flexible mesh for TAU volume mesh. The default is ``False``.
        curvilinear : bool, optional
            Whether to apply curvilinear elements. The default is ``False``.
        fallback : bool, optional
            Whether to retain as a fallback. The default is ``True``.
        phi : bool, optional
            Whether to use the Phi mesher for layered geometry.
            The default is ``True``.
        auto_model_resolution : bool, optional
            Whether to automatically calculate the resolution length
            based on each object's effective thickness. The default is ``True``.
        model_resolution_length : float, optional
             Resolution thickness with units if ``automodelresolution=False``.
             The default ``"0.0001mm"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.InitialMeshSettings
        """
        if self._app.design_type in ["2D Extractor", "Maxwell 2D"]:
            mesh_methods = ["Auto", "AnsoftClassic"]
        else:
            mesh_methods = ["Auto", "AnsoftTAU", "AnsoftClassic"]
        if method not in mesh_methods:
            raise ValueError(f"Invalid mesh method {method}")

        modelres = ["NAME:GlobalModelRes", "UseAutoLength:=", auto_model_resolution]
        if not auto_model_resolution:
            modelres += ["DefeatureLength:=", model_resolution_length]
        surface_appr = [
            "NAME:GlobalSurfApproximation",
            "CurvedSurfaceApproxChoice:=",
            "UseSlider",
            "SliderMeshSettings:=",
            level,
        ]

        if self._app.design_type in ["2D Extractor", "Maxwell 2D"]:
            args = ["NAME:MeshSettings", surface_appr, modelres, "MeshMethod:=", method]
        else:
            args = [
                "NAME:MeshSettings",
                surface_appr,
                ["NAME:GlobalCurvilinear", "Apply:=", curvilinear],
                modelres,
                "MeshMethod:=",
                method,
                "UseLegacyFaceterForTauVolumeMesh:=",
                False,
                "DynamicSurfaceResolution:=",
                dynamic_surface,
                "UseFlexMeshingForTAUvolumeMesh:=",
                flex_mesh,
            ]
        if self._app.design_type == "HFSS":
            args += ["UseAlternativeMeshMethodsAsFallBack:=", fallback, "AllowPhiForLayeredGeometry:=", phi]
        self.omeshmodule.InitialMeshSettings(args)
        return True

    @pyaedt_function_handler()
    def assign_initial_mesh(
        self,
        method="Auto",
        surface_deviation=None,
        normal_deviation=None,
        aspect_ratio=None,
        flex_mesh=False,
        curvilinear=False,
        fallback=True,
        phi=True,
        auto_model_resolution=True,
        model_resolution_length="0.0001mm",
    ):
        """Assign a surface mesh level to an object.

        Parameters
        ----------
        method : str, optional
            Meshing method. Options are ``"Auto"``, ``"AnsoftTAU"``, and ``"AnsoftClassic"``
            The default is ``"Auto"``.
        surface_deviation : float or str, optional
             Surface deviation.
             The default is ``None``, in which case the default value is assigned.
        normal_deviation : float or str, optional
             Normal deviation.
             The default is ``None``, in which case the default value is assigned.
        aspect_ratio : float or str, optional
             Aspect ratio.
             The default is ``None``, in which case the default value is assigned.
        flex_mesh : bool, optional
            Whether to use flexible mesh for TAU volume mesh. The default is ``False``.
        curvilinear : bool, optional
            Whether to apply curvilinear elements. The default is ``False``.
        fallback : bool, optional
            Whether to retain as a fallback. The default is ``True``.
        phi : bool, optional
            Whether to use the Phi mesher for layered geometry.
            The default is ``True``.
        auto_model_resolution : bool, optional
            Whether to automatically calculate the resolution length
            based on each object's effective thickness. The default is ``True``.
        model_resolution_length : float or str, optional
             Resolution thickness with units if ``automodelresolution=False``.
             The default ``"0.0001mm"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.InitialMeshSettings
        """
        if self._app.design_type in ["2D Extractor", "Maxwell 2D"]:
            mesh_methods = ["Auto", "AnsoftClassic"]
        else:
            mesh_methods = ["Auto", "AnsoftTAU", "AnsoftClassic"]
        if method not in mesh_methods:
            raise ValueError(f"Invalid mesh method {method}")

        modelres = ["NAME:GlobalModelRes", "UseAutoLength:=", auto_model_resolution]
        if not auto_model_resolution:
            modelres.append("DefeatureLength:=")
            modelres.append(model_resolution_length)

        surface_appr = [
            "NAME:GlobalSurfApproximation",
            "CurvedSurfaceApproxChoice:=",
            "ManualSettings",
            "SurfDevChoice:=",
        ]

        if not surface_deviation:
            surface_appr.append(0)
        else:
            surface_appr += [2, "SurfDev:=", surface_deviation]

        surface_appr.append("NormalDevChoice:=")
        if not normal_deviation:
            surface_appr.append(1)
        else:
            surface_appr += [2, "NormalDev:=", normal_deviation]

        surface_appr.append("AspectRatioChoice:=")
        if not aspect_ratio:
            surface_appr.append(1)
        else:
            surface_appr += [2, "AspectRatio:=", aspect_ratio]

        if self._app.design_type in ["2D Extractor", "Maxwell 2D"]:
            args = ["NAME:MeshSettings", surface_appr, modelres, "MeshMethod:=", method]
        else:
            args = [
                "NAME:MeshSettings",
                surface_appr,
                ["NAME:GlobalCurvilinear", "Apply:=", curvilinear],
                modelres,
                "MeshMethod:=",
                method,
                "UseLegacyFaceterForTauVolumeMesh:=",
                False,
                "DynamicSurfaceResolution:=",
                False,
                "UseFlexMeshingForTAUvolumeMesh:=",
                flex_mesh,
            ]
        if self._app.design_type == "HFSS":
            args += ["UseAlternativeMeshMethodsAsFallBack:=", fallback, "AllowPhiForLayeredGeometry:=", phi]
        self.omeshmodule.InitialMeshSettings(args)
        return True

    @pyaedt_function_handler(object_lists="assignment", surfpriority="surface_priority")
    def assign_surf_priority_for_tau(self, assignment, surface_priority=0):
        """Assign a surface representation priority for the TAU mesh.

        Parameters
        ----------
        assignment : list
            List of objects to apply a surface representation
            priority to.
        surface_priority : int, optional
            Surface representation priority. The default is ``0``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.AssignSurfPriorityForTauOp
        """
        meshop_name = generate_unique_name("SurfaceRepPriority")
        props = dict({"Type": "SurfaceRepPriority", "Objects": assignment, "SurfaceRepPriority": surface_priority})
        mop = MeshOperation(self, meshop_name, props, "SurfaceRepPriority")
        mop.create()
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler()
    def generate_mesh(self, name):
        """Generate the mesh for a design.

        Parameters
        ----------
        name : str
            Name of the simulation setup.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.GenerateMesh

        Examples
        --------

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> m3d.create_setup(setupname="Setup1")
        >>> m3d.mesh.assign_length_mesh(maxlength=5, maxel="None")
        >>> m3d.mesh.generate_mesh("Setup1")

        """
        return self._odesign.GenerateMesh(name) == 0

    @pyaedt_function_handler()
    def delete_mesh_operations(self, mesh_type=None):
        """Remove mesh operations from a design.

        Parameters
        ----------
        mesh_type : optional
           Type of the mesh operation to delete. The default is ``None``, in which
           case all mesh operations are deleted.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.DeleteOp
        """
        mesh_op_types = ["Length Based", "Surface Approximation Based"]

        if mesh_type:
            if mesh_type in mesh_op_types:
                mesh_op_types = [mesh_type]

        for mesh_op_type in mesh_op_types:
            opnames = self.omeshmodule.GetOperationNames(mesh_op_type)
            if opnames:
                self.omeshmodule.DeleteOp(opnames)
            for el in self.meshoperations[:]:
                if el.name in opnames:
                    self.meshoperations.remove(el)

        return True

    @pyaedt_function_handler(
        names="assignment",
        isinside="inside_selection",
        maxlength="maximum_length",
        maxel="maximum_elements",
        meshop_name="name",
    )
    def assign_length_mesh(self, assignment, inside_selection=True, maximum_length=1, maximum_elements=1000, name=None):
        """Assign a length for the model resolution.

        Parameters
        ----------
        assignment : list, str
            List of object names or face IDs.
        inside_selection : bool, optional
            Whether the length mesh is inside the selection. The default is ``True``.
        maximum_length : str, float, optional
            Maximum element length. The default is ``1``. When ``None``,
            this parameter is disabled.
        maximum_elements : int, optional
            Maximum number of elements. The default is ``1000``. When ``None``, this parameter
            is disabled.
        name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.AssignLengthOp
        """
        assignment = self._modeler.convert_to_selections(assignment, True)
        if name:
            for m in self.meshoperations:
                if name == m.name:  # If the mesh operation name exists, find a new, unique name.
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("length")

        if maximum_length is None:
            restrictlength = False
        else:
            restrictlength = True
        length = self._modeler.modeler_variable(maximum_length)

        if maximum_elements is None:
            restrictel = False
            numel = "1000"
        else:
            restrictel = True
            numel = str(maximum_elements)
        if maximum_length is None and maximum_elements is None:
            self.logger.error("mesh not assigned due to incorrect settings")
            return

        if isinstance(assignment[0], int) and not inside_selection:
            seltype = "Faces"
        elif isinstance(assignment[0], str):
            seltype = "Objects"
        else:
            seltype = None
        if seltype is None:
            self.logger.error("Error in Assignment")
            return
        props = dict(
            {
                "Type": "LengthBased",
                "RefineInside": inside_selection,
                "Enabled": True,
                seltype: assignment,
                "RestrictElem": restrictel,
                "NumMaxElem": numel,
                "RestrictLength": restrictlength,
                "MaxLength": length,
            }
        )

        mop = MeshOperation(self, name, props, "LengthBased")

        for meshop in self.meshoperations[:]:
            if meshop.name == mop.name:
                meshop.delete()
                break

        mop.create()
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler(
        names="assignment",
        skindepth="skin_depth",
        maxelements="maximum_elements",
        numlayers="layers_number",
        meshop_name="name",
    )
    def assign_skin_depth(
        self,
        assignment,
        skin_depth="0.2mm",
        maximum_elements=None,
        triangulation_max_length="0.1mm",
        layers_number="2",
        name=None,
    ):
        """Assign a skin depth for the mesh refinement.

        Parameters
        ----------
        assignment : list
           List of the object names, face IDs or edges IDs for Maxwell 2D design.
        skin_depth : str, float, optional
            Skin depth value.
            It can be either provided as a float or as a string.
            The default is ``"0.2mm"``.
        maximum_elements : int, optional
            Maximum number of elements. The default is ``None``, which means this parameter is disabled.
        triangulation_max_length : str, optional
            Maximum surface triangulation length with units. The default is ``"0.1mm"``.
        layers_number : str, optional
            Number of layers. The default is ``"2"``.
        name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.AssignSkinDepthOp
        """
        assignment = self._modeler.convert_to_selections(assignment, True)

        if self._app.design_type not in ["HFSS", "Maxwell 3D", "Maxwell 2D"]:
            raise MethodNotSupportedError
        if name:
            for m in self.meshoperations:
                if name == m.name:
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("SkinDepth")

        if self._app.design_type == "Maxwell 2D":
            props = dict(
                {
                    "Edges": assignment,
                    "SkinDepth": skin_depth,
                    "NumLayers": layers_number,
                }
            )
        else:
            if maximum_elements is None:
                restrictlength = False
                maximum_elements = "1000"
            else:
                restrictlength = True

            if isinstance(assignment[0], int):
                seltype = "Faces"
            elif isinstance(assignment[0], str):
                seltype = "Objects"

            props = dict(
                {
                    "Type": "SkinDepthBased",
                    "Enabled": True,
                    seltype: assignment,
                    "RestrictElem": restrictlength,
                    "NumMaxElem": str(maximum_elements),
                    "SkinDepth": skin_depth,
                    "SurfTriMaxLength": triangulation_max_length,
                    "NumLayers": layers_number,
                }
            )

        mop = MeshOperation(self, name, props, "SkinDepthBased")
        mop.create()
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler(names="assignment", meshop_name="name")
    def assign_curvilinear_elements(self, assignment, enable=True, name=None):
        """Assign curvilinear elements.

        Parameters
        ----------
        assignment : list
            List of objects or faces.
        enable : bool, optional
            Whether to apply curvilinear elements. The default is ``True``.
        name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.AssignApplyCurvlinearElementsOp
        """
        assignment = self._modeler.convert_to_selections(assignment, True)

        if self._app.design_type != "HFSS" and self._app.design_type != "Maxwell 3D":
            raise MethodNotSupportedError
        if name:
            for m in self.meshoperations:
                if name == m.name:
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("CurvilinearElements")

        if isinstance(assignment[0], int):
            seltype = "Faces"
        elif isinstance(assignment[0], str):
            seltype = "Objects"
        else:
            seltype = None
        if seltype is None:
            self.logger.error("Error in Assignment")
            return
        props = dict({"Type": "Curvilinear", seltype: assignment, "Apply": enable})
        mop = MeshOperation(self, name, props, "Curvilinear")
        mop.create()
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler(
        names="assignment", disable_for_faceted_surf="disabled_for_faceted", meshoperation_names="name"
    )
    def assign_curvature_extraction(self, assignment, disabled_for_faceted=True, name=None):
        """Assign curvature extraction.

        Parameters
        ----------
        assignment : list
        List of objects or faces.
        disabled_for_faceted : bool, optional
        Whether curvature extraction is enabled for faceted surfaces.
        The default is ``True``.
        name : str, optional
        Name of the mesh operation. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.AssignCurvatureExtractionOp
        """
        assignment = self._modeler.convert_to_selections(assignment, True)

        if self._app.solution_type != "SBR+":
            raise MethodNotSupportedError
        if name:
            for m in self.meshoperations:
                if name == m.name:
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("CurvilinearElements")
        assignment = self._app.modeler.convert_to_selections(assignment, True)
        if isinstance(assignment[0], int):
            seltype = "Faces"
        elif isinstance(assignment[0], str):
            seltype = "Objects"
        else:
            seltype = None
        if seltype is None:
            self.logger.error("Error in Assignment")
            return
        props = dict(
            {"Type": "CurvatureExtraction", seltype: assignment, "DisableForFacetedSurfaces": disabled_for_faceted}
        )
        mop = MeshOperation(self, name, props, "CurvatureExtraction")
        mop.create()
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler(names="assignment", num_layers="layers_number", meshop_name="name")
    def assign_rotational_layer(self, assignment, layers_number=3, total_thickness="1mm", name=None):
        """Assign a rotational layer mesh.

        Parameters
        ----------
        assignment : list
            List of objects.
        layers_number : int, optional
            Number of layers to create in the radial direction, starting from
            the faces most adjacent to the band. The default is ``3``, which is the maximum.
        total_thickness : str, optional
            Total thickness of all layers with units. The default is ``"1mm"``.
        name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.AssignRotationalLayerOp
        """
        assignment = self._modeler.convert_to_selections(assignment, True)

        if self._app.design_type != "Maxwell 3D":
            raise MethodNotSupportedError
        if name:
            for m in self.meshoperations:
                if name == m.name:
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("RotationalLayer")
        seltype = "Objects"
        props = dict(
            {
                "Type": "RotationalLayerMesh",
                seltype: assignment,
                "Number of Layers": str(layers_number),
                "Total Layer Thickness": total_thickness,
            }
        )

        mop = MeshOperation(self, name, props, "RotationalLayerMesh")
        mop.create()
        mop.props["Total Layer Thickness"] = total_thickness
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler(names="assignment", meshop_name="name")
    def assign_edge_cut(self, assignment, layer_thickness="1mm", name=None):
        """Assign an edge cut layer mesh.

        Parameters
        ----------
        assignment : list
            List of objects.
        layer_thickness :
            Thickness of the layer with units. The default is ``"1mm"``.
        name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.AssignRotationalLayerOp
        """
        assignment = self._modeler.convert_to_selections(assignment, True)

        if self._app.design_type != "Maxwell 3D":
            raise MethodNotSupportedError
        if name:
            for m in self.meshoperations:
                if name == m.name:
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("EdgeCut")
        seltype = "Objects"
        props = dict({"Type": "EdgeCutLayerMesh", seltype: assignment, "Layer Thickness": layer_thickness})

        mop = MeshOperation(self, name, props, "EdgeCutLayerMesh")
        mop.create()
        mop.props["Layer Thickness"] = layer_thickness
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler(
        names="assignment", maxelementlength="maximum_element_length", layerNum="layers_number", meshop_name="name"
    )
    def assign_density_control(
        self, assignment, refine_inside=True, maximum_element_length=None, layers_number=None, name=None
    ):
        """Assign density control.

        Parameters
        ----------
        assignment : list
            List of objects.
        refine_inside : bool, optional
            Whether to refine inside objects. The default is ``True``.
        maximum_element_length : str, optional
            Maximum element length with units. The default is ``None``,
            which disables this parameter.
        layers_number : int, optional
            Number of layers. The default is ``None``, which disables
            this parameter.
        name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation`
            Mesh operation object.

        References
        ----------
        >>> oModule.AssignDensityControlOp
        """
        assignment = self._modeler.convert_to_selections(assignment, True)

        if self._app.design_type != "Maxwell 3D":
            raise MethodNotSupportedError
        if name:
            for m in self.meshoperations:
                if name == m.name:
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("CloneMeshDensity")
        seltype = "Objects"
        if not maximum_element_length:
            restr = False
            restrval = "0mm"
        else:
            restr = True
            restrval = maximum_element_length
        if not layers_number:
            restrlay = False
            restrlaynum = "1"
        else:
            restrlay = True
            restrlaynum = str(layers_number)
        props = dict(
            {
                "Type": "DensityControlBased",
                "RefineInside": refine_inside,
                seltype: assignment,
                "RestrictMaxElemLength": restr,
                "MaxElemLength": restrval,
                "RestrictLayersNum": restrlay,
                "LayersNum": restrlaynum,
            }
        )
        mop = MeshOperation(self, name, props, "DensityControlBased")
        mop.create()
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler(obj="entity", meshop_name="name")
    def assign_cylindrical_gap(
        self,
        entity,
        name=None,
        band_mapping_angle=None,
        clone_mesh=False,
        moving_side_layers=1,
        static_side_layers=1,
    ):
        """Assign a cylindrical gap for a 2D or 3D design to enable a clone mesh and associated band mapping angle.

        Parameters
        ----------
        entity : int or str or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Object to assign cylindrical gap to.
        name : str, optional
            Name of the mesh. The default is ``None``, in which
            case the default name is used.
        clone_mesh : bool, optional
            Whether to clone the mesh. This parameter is valid only for 3D design.
            The default is ``False``. If ``True``, the solid bodies adjacent to the band
            are detected to identify the clone object.
        band_mapping_angle : int, optional
            Band mapping angle in degrees.
            The recommended band mapping angle (the angle the rotor rotates in one time step) typically
            equals the rotational speed multiplied by the time step.
            The band mapping angle must be between 0.0005 and 3 degrees.
            The default is ``None``.

            - For a 2D design, if a value is provided, the option ``Use band mapping angle``
              is automatically enabled.
            - For a 3D design, the ``Clone Mesh`` option has to be enabled first.
        moving_side_layers : int, optional
            Number of mesh layers on the moving side.
            The valid ranges are integers greater or equal to 1.
            This parameter is valid only for a 3D design.
            The default is ``1``.
        static_side_layers : int, optional
            Number of mesh layers on the static side.
            The valid ranges are integers greater than or equal to 1.
            This parameter is valid only for a 3D design.
            The default is ``1``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.mesh.MeshOperation` or bool
            Mesh operation object or ``False`` if it fails.

        References
        ----------
        >>> oModule.AssignCylindricalGapOp
        """
        try:
            if self._app.design_type != "Maxwell 2D" and self._app.design_type != "Maxwell 3D":
                raise MethodNotSupportedError

            entity = self._modeler.convert_to_selections(entity, True)
            if len(entity) > 1:
                self.logger.error("Cylindrical gap treatment cannot be assigned to multiple objects.")
                raise ValueError
            if [x for x in self.meshoperations if x.type == "Cylindrical Gap Based" or x.type == "CylindricalGap"]:
                self.logger.error("Cylindrical gap treatment cannot be assigned to multiple objects.")
                raise ValueError
            if band_mapping_angle and band_mapping_angle > 3:
                self.logger.error("Band mapping angle must be between 0.0005 and 3 deg.")
                raise ValueError
            if not name:
                name = generate_unique_name("CylindricalGap")

            if self._app.design_type == "Maxwell 3D":
                if moving_side_layers < 1:
                    self.logger.error("Moving side layers must be an integer greater or equal to 1.")
                    raise ValueError
                if static_side_layers < 1:
                    self.logger.error("Static side layers must be an integer greater or equal to 1.")
                    raise ValueError
                if clone_mesh and not band_mapping_angle:
                    band_mapping_angle = 3
                props = dict(
                    {
                        "Name": name,
                        "Objects": entity,
                        "CloneMesh": clone_mesh,
                        "BandMappingAngle": str(band_mapping_angle) + "deg",
                        "MovingSideLayers": moving_side_layers,
                        "StaticSideLayers": static_side_layers,
                    }
                )
            elif self._app.design_type == "Maxwell 2D":
                if band_mapping_angle:
                    use_band_mapping_angle = True
                else:
                    use_band_mapping_angle = False
                    band_mapping_angle = 3
                props = dict(
                    {
                        "Name": name,
                        "Objects": entity,
                        "UseBandMappingAngle": use_band_mapping_angle,
                        "BandMappingAngle": str(band_mapping_angle) + "deg",
                    }
                )
            mesh_operation = MeshOperation(self, name, props, "CylindricalGap")
            mesh_operation.create()
            self.meshoperations.append(mesh_operation)
            return mesh_operation
        except Exception:
            return False
