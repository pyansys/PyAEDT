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

"""
This module contains these classes: `Mesh` and `Mesh3DOperation`.

This module provides all functionalities for creating and editing the mesh in the 3D tools.

"""

from ansys.aedt.core.generic.data_handlers import _dict2arg
from ansys.aedt.core.generic.general_methods import PropsManager
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modules.mesh import MeshProps


class Mesh3DOperation(PropsManager, object):
    """Mesh3DOperation class.

    Parameters
    ----------
    app :

    hfss_setup_name : str
        Name of the HFSS setup.
    name :

    props : dict
        Dictionary of the properties.

    """

    def __init__(self, app, hfss_setup_name, name, props):
        self.auto_update = True
        self._mesh3dlayout = app
        self.name = name
        self.props = MeshProps(self, props)
        self.hfss_setup_name = hfss_setup_name

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        """Retrieve arguments.

        Parameters
        ----------
        props : dict
            Dictionary of the properties. The default is ``None``, in which
            case the default properties are retrieved.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if not props:
            props = self.props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg

    @pyaedt_function_handler()
    def create(self):
        """Create a mesh.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AddMeshOperation
        """
        self._mesh3dlayout.omeshmodule.AddMeshOperation(self.hfss_setup_name, self._get_args())
        return True

    @pyaedt_function_handler()
    def update(self, *args, **kwargs):
        """Update the mesh.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.EditMeshOperation
        """
        self._mesh3dlayout.omeshmodule.EditMeshOperation(self.hfss_setup_name, self.name, self._get_args())
        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete the mesh.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.DeleteMeshOperation
        """
        self._mesh3dlayout.omeshmodule.DeleteMeshOperation(
            self.hfss_setup_name,
            self.name,
        )

        return True


class Mesh3d(object):
    """Manages mesh operations for HFSS 3D Layout.

    Provides the main AEDT mesh functionality. The inherited class
    ``AEDTConfig`` contains all ``_desktop`` hierarchical calls needed by this class.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_3d_layout.FieldAnalysis3DLayout`

    """

    def __init__(self, app):
        app.logger.reset_timer()
        self._app = app

        self.logger = self._app.logger
        self._odesign = self._app._odesign
        self.modeler = self._app.modeler
        self.id = 0

        self.meshoperations = self._get_design_mesh_operations()

        app.logger.info_timer("Mesh class has been initialized!")

    @pyaedt_function_handler()
    def generate_mesh(self, name):
        """Generate the mesh for a design.

        Parameters
        ----------
        name : str
            Name of the design.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.GenerateMesh
        """
        self._app.oanalysis.GenerateMesh([name])
        return True

    @property
    def omeshmodule(self):
        """AEDT Mesh Module.

        References
        ----------
        >>> oDesign.GetModule("SolveSetups")
        """
        return self._app.omeshmodule

    @pyaedt_function_handler(setup_name="setup", mesh_name="name")
    def delete_mesh_operations(self, setup, name):
        """Remove mesh operations from a setup.

        Parameters
        ----------
        setup : str
            Name of the setup.
        name : str
            Name of the mesh.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.DeleteMeshOperation
        """
        for el in self.meshoperations:
            if el.hfss_setup_name == setup and el.name == name:
                el.delete()
                self.meshoperations.remove(el)

        return True

    @pyaedt_function_handler()
    def _get_design_mesh_operations(self):
        """Retrieve design mesh operations.

        Returns
        -------
        type
            Mesh operations object.

        """
        meshops = []
        try:
            for ds in self._app.design_properties["Setup"]["Data"]:
                if "MeshOps" in self._app.design_properties["Setup"]["Data"][ds]:
                    for ops in self._app.design_properties["Setup"]["Data"][ds]["MeshOps"]:
                        props = self._app.design_properties["Setup"]["Data"][ds]["MeshOps"][ops]
                        meshops.append(Mesh3DOperation(self, ds, ops, props))
        except Exception:
            self.logger.debug("An error occurred while accessing design mesh operations.")  # pragma: no cover
        return meshops

    @pyaedt_function_handler(
        setupname="setup",
        layer_name="layer",
        net_name="net",
        isinside="is_inside",
        maxlength="maximum_length",
        maxel="maximum_elements",
        meshop_name="name",
    )
    def assign_length_mesh(self, setup, layer, net, is_inside=True, maximum_length=1, maximum_elements=1000, name=None):
        """Assign mesh length.

        Parameters
        ----------
        setup : str
            Name of the HFSS setup to apply.
        layer : str
           Name of the layer.
        net : str
           Name of the net.
        is_inside : bool, optional
            Whether the mesh length is inside the selection. The default is ``True``.
        maximum_length : float, optional
            Maximum length of the element. The default is ``1`` When ``None``, this
            parameter is disabled.
        maximum_elements : int, optional
            Maximum number of elements. The default is ``1000``. When ``None``, this
            parameter is disabled.
        name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        type
            Mesh operation object.

        References
        ----------
        >>> oModule.AddMeshOperation
        """
        if name:
            for el in self.meshoperations:
                if el.name == name:
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("Length")

        if maximum_length is None:
            restrictlength = False
        else:
            restrictlength = True
        length = self.modeler.modeler_variable(maximum_length)

        if maximum_elements is None:
            restrictel = False
            numel = "1000"
        else:
            restrictel = True
            numel = str(maximum_elements)
        if maximum_length is None and maximum_elements is None:
            self.logger.error("mesh not assigned due to incorrect settings")
            return
        if isinstance(layer, list) and isinstance(net, list):
            assignment = dict({"MeshEntityInfo": []})
            for l, n in zip(layer, net):
                meshbody = dict({"Id": -1, "Nam": "", "Layer": l, "Net": n, "OrigNet": n})
                assignment["MeshEntityInfo"].append(
                    dict({"IsFcSel": False, "EntID": -1, "FcIDs": [], "MeshBody": meshbody, "BBox": []})
                )
        else:
            meshbody = dict({"Id": -1, "Nam": "", "Layer": layer, "Net": net, "OrigNet": net})
            assignment = dict(
                {"MeshEntityInfo": dict({"IsFcSel": False, "EntID": -1, "FcIDs": [], "MeshBody": meshbody, "BBox": []})}
            )
        props = dict(
            {
                "Type": "LengthBased",
                "RefineInside": is_inside,
                "Enabled": True,
                "Assignment": assignment,
                "Region": "",
                "RestrictElem": restrictel,
                "NumMaxElem": numel,
                "RestrictLength": restrictlength,
                "MaxLength": length,
            }
        )

        mop = Mesh3DOperation(self, setup, name, props)
        mop.create()
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler(
        setupname="setup",
        layer_name="layer",
        net_name="net",
        skindepth="skin_depth",
        maxelements="maximum_elements",
        numlayers="layers_number",
        meshop_name="name",
    )
    def assign_skin_depth(
        self,
        setup,
        layer,
        net,
        skin_depth=1,
        maximum_elements=None,
        triangulation_max_length=0.1,
        layers_number="2",
        name=None,
    ):
        """Assign skin depth to the mesh.

        Parameters
        ----------
        setup : str
            Name of the setup.
        layer : str
            Name of the layer.
        net : str
            Name of the net.
        skin_depth : int, optional
            Depth of the skin. The default is ``1``.
        maximum_elements : float, optional
            Maximum element length. The default is ``None``, which disables this parameter.
        triangulation_max_length : float, optional
            Maximum surface triangulation length. The default is ``0.1``.
        layers_number : str, optional
            Number of layers. The default is ``"2"``.
        name : str, optional
             Name of the mesh operation. The default is ``None``.

        Returns
        -------
        type
            Mesh operation object.

        References
        ----------
        >>> oModule.AddMeshOperation
        """
        if name:
            for el in self.meshoperations:
                if el.name == name:
                    name = generate_unique_name(name)
        else:
            name = generate_unique_name("SkinDepth")

        if maximum_elements is None:
            restrictlength = False
            maximum_elements = "1000"
        else:
            restrictlength = True
        skin_depth = self.modeler.modeler_variable(skin_depth)
        triangulation_max_length = self.modeler.modeler_variable(triangulation_max_length)
        meshbody = dict({"Id": -1, "Nam": "", "Layer": layer, "Net": net, "OrigNet": net})
        assignment = dict(
            {"MeshEntityInfo": dict({"IsFcSel": False, "EntID": -1, "FcIDs": [], "MeshBody": meshbody, "BBox": []})}
        )
        props = dict(
            {
                "Type": "SkinDepthLengthBased",
                "Enabled": True,
                "Assignment": assignment,
                "Region": "",
                "SkinDepth": skin_depth,
                "SurfTriMaxLength": triangulation_max_length,
                "NumLayers": layers_number,
                "RestrictElem": restrictlength,
                "NumMaxElem": maximum_elements,
            }
        )

        mop = Mesh3DOperation(self, setup, name, props)
        mop.create()
        self.meshoperations.append(mop)
        return mop
