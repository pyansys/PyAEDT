"""This module contains these classes: `Mesh` and `Mesh3DOperation`.

This module provides all functionalities for creating and editing the mesh in the 3D tools.

"""
from __future__ import absolute_import  # noreorder

from collections import OrderedDict

from pyaedt.generic.DataHandlers import _dict2arg
from pyaedt.generic.general_methods import PropsManager, generate_unique_name, pyaedt_function_handler
from pyaedt.modules.Mesh import MeshProps


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
    app : :class:`pyaedt.application.Analysis3DLayout.FieldAnalysis3DLayout`

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

    @pyaedt_function_handler()
    def delete_mesh_operations(self, setup_name, mesh_name):
        """Remove mesh operations from a setup.

        Parameters
        ----------
        setup_name : str
            Name of the setup.
        mesh_name : str
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
            if el.hfss_setup_name == setup_name and el.name == mesh_name:
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
        except:
            pass
        return meshops

    @pyaedt_function_handler()
    def assign_length_mesh(
        self, setupname, layer_name, net_name, isinside=True, maxlength=1, maxel=1000, meshop_name=None
    ):
        """Assign mesh length.

        Parameters
        ----------
        setupname : str
            Name of the HFSS setup to apply.
        layer_name : str
           Name of the layer.
        net_name : str
           Name of the net.
        isinside : bool, optional
            Whether the mesh length is inside the selection. The default is ``True``.
        maxlength : float, optional
            Maximum length of the element. The default is ``1`` When ``None``, this
            parameter is disabled.
        maxel : int, optional
            Maximum number of elements. The default is ``1000``. When ``None``, this
            parameter is disabled.
        meshop_name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        type
            Mesh operation object.

        References
        ----------
        >>> oModule.AddMeshOperation
        """
        if meshop_name:
            for el in self.meshoperations:
                if el.name == meshop_name:
                    meshop_name = generate_unique_name(meshop_name)
        else:
            meshop_name = generate_unique_name("Length")

        if maxlength is None:
            restrictlength = False
        else:
            restrictlength = True
        length = self.modeler.modeler_variable(maxlength)

        if maxel is None:
            restrictel = False
            numel = "1000"
        else:
            restrictel = True
            numel = str(maxel)
        if maxlength is None and maxel is None:
            self.logger.error("mesh not assigned due to incorrect settings")
            return
        if isinstance(layer_name, list) and isinstance(net_name, list):
            assignment = OrderedDict({"MeshEntityInfo": []})
            for l, n in zip(layer_name, net_name):
                meshbody = OrderedDict({"Id": -1, "Nam": "", "Layer": l, "Net": n, "OrigNet": n})
                assignment["MeshEntityInfo"].append(
                    OrderedDict({"IsFcSel": False, "EntID": -1, "FcIDs": [], "MeshBody": meshbody, "BBox": []})
                )
        else:
            meshbody = OrderedDict({"Id": -1, "Nam": "", "Layer": layer_name, "Net": net_name, "OrigNet": net_name})
            assignment = OrderedDict(
                {
                    "MeshEntityInfo": OrderedDict(
                        {"IsFcSel": False, "EntID": -1, "FcIDs": [], "MeshBody": meshbody, "BBox": []}
                    )
                }
            )
        props = OrderedDict(
            {
                "Type": "LengthBased",
                "RefineInside": isinside,
                "Enabled": True,
                "Assignment": assignment,
                "Region": "",
                "RestrictElem": restrictel,
                "NumMaxElem": numel,
                "RestrictLength": restrictlength,
                "MaxLength": length,
            }
        )

        mop = Mesh3DOperation(self, setupname, meshop_name, props)
        mop.create()
        self.meshoperations.append(mop)
        return mop

    @pyaedt_function_handler()
    def assign_skin_depth(
        self,
        setupname,
        layer_name,
        net_name,
        skindepth=1,
        maxelements=None,
        triangulation_max_length=0.1,
        numlayers="2",
        meshop_name=None,
    ):
        """Assign skin depth to the mesh.

        Parameters
        ----------
        setupname : str
            Name of the setup.
        layer_name : str
            Name of the layer.
        net_name : str
            Name of the net.
        skindepth : int, optional
            Depth of the skin. The default is ``1``.
        maxelements : float, optional
            Maximum element length. The default is ``None``, which disables this parameter.
        triangulation_max_length : float, optional
            Maximum surface triangulation length. The default is ``0.1``.
        numlayers : str, optional
            Number of layers. The default is ``"2"``.
        meshop_name : str, optional
             Name of the mesh operation. The default is ``None``.

        Returns
        -------
        type
            Mesh operation object.

        References
        ----------
        >>> oModule.AddMeshOperation
        """
        if meshop_name:
            for el in self.meshoperations:
                if el.name == meshop_name:
                    meshop_name = generate_unique_name(meshop_name)
        else:
            meshop_name = generate_unique_name("SkinDepth")

        if maxelements is None:
            restrictlength = False
            maxelements = "1000"
        else:
            restrictlength = True
        skindepth = self.modeler.modeler_variable(skindepth)
        triangulation_max_length = self.modeler.modeler_variable(triangulation_max_length)
        meshbody = OrderedDict({"Id": -1, "Nam": "", "Layer": layer_name, "Net": net_name, "OrigNet": net_name})
        assignment = OrderedDict(
            {
                "MeshEntityInfo": OrderedDict(
                    {"IsFcSel": False, "EntID": -1, "FcIDs": [], "MeshBody": meshbody, "BBox": []}
                )
            }
        )
        props = OrderedDict(
            {
                "Type": "SkinDepthLengthBased",
                "Enabled": True,
                "Assignment": assignment,
                "Region": "",
                "SkinDepth": skindepth,
                "SurfTriMaxLength": triangulation_max_length,
                "NumLayers": numlayers,
                "RestrictElem": restrictlength,
                "NumMaxElem": maxelements,
            }
        )

        mop = Mesh3DOperation(self, setupname, meshop_name, props)
        mop.create()
        self.meshoperations.append(mop)
        return mop
