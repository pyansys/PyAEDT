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

from ansys.aedt.core.generic.data_handlers import _dict2arg
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modeler.cad.elements_3d import BinaryTreeNode
from ansys.aedt.core.modules.boundary.common import BoundaryCommon
from ansys.aedt.core.modules.boundary.common import BoundaryProps


class MaxwellParameters(BoundaryCommon, BinaryTreeNode):
    """Manages parameters data and execution.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.maxwell.Maxwell3d`, :class:`ansys.aedt.core.maxwell.Maxwell2d`
        Either ``Maxwell3d`` or ``Maxwell2d`` application.
    name : str
        Name of the boundary.
    props : dict, optional
        Properties of the boundary.
    boundarytype : str, optional
        Type of the boundary.

    Examples
    --------

    Create a matrix in Maxwell3D return a ``ansys.aedt.core.modules.boundary.common.BoundaryObject``

    >>> from ansys.aedt.core import Maxwell2d
    >>> maxwell_2d = Maxwell2d()
    >>> coil1 = maxwell_2d.modeler.create_rectangle([8.5,1.5, 0],[8, 3],True,"Coil_1","vacuum")
    >>> coil2 = maxwell_2d.modeler.create_rectangle([8.5,1.5, 0],[8, 3],True,"Coil_2","vacuum")
    >>> maxwell_2d.assign_matrix(["Coil_1", "Coil_2"])
    """

    def __init__(self, app, name, props=None, boundarytype=None):
        self.auto_update = False
        self._app = app
        self._name = name
        self.__props = BoundaryProps(self, props) if props else {}
        self.type = boundarytype
        self.auto_update = True
        self.__reduced_matrices = None
        self.matrix_assignment = None
        self._initialize_tree_node()

    @property
    def reduced_matrices(self):
        """List of reduced matrix groups for the parent matrix.

        Returns
        -------
        dict
            Dictionary of reduced matrices where the key is the name of the parent matrix
            and the values are in a list of reduced matrix groups.
        """
        if self._app.solution_type == "EddyCurrent":
            self.__reduced_matrices = {}
            cc = self._app.odesign.GetChildObject("Parameters")
            parents = cc.GetChildNames()
            if self.name in parents:
                parent_object = self._app.odesign.GetChildObject("Parameters").GetChildObject(self.name)
                parent_type = parent_object.GetPropValue("Type")
                if parent_type == "Matrix":
                    self.matrix_assignment = parent_object.GetPropValue("Selection").split(",")
                    child_names = parent_object.GetChildNames()
                    self.__reduced_matrices = []
                    for r in child_names:
                        self.__reduced_matrices.append(MaxwellMatrix(self._app, self.name, r))
        return self.__reduced_matrices

    @property
    def _child_object(self):

        cc = self._app.odesign.GetChildObject("Parameters")
        child_object = None
        if self._name in cc.GetChildNames():
            child_object = self._app.odesign.GetChildObject("Parameters").GetChildObject(self._name)
        elif self._name in self._app.odesign.GetChildObject("Parameters").GetChildNames():
            child_object = self._app.odesign.GetChildObject("Parameters").GetChildObject(self._name)

        return child_object

    @property
    def props(self):
        """Maxwell parameter data.

        Returns
        -------
        :class:BoundaryProps
        """
        if self.__props:
            return self.__props
        props = self._get_boundary_data(self.name)

        if props:
            self.__props = BoundaryProps(self, props[0])
            self._type = props[1]
        return self.__props

    @property
    def name(self):
        """Boundary Name."""
        if self._child_object:
            self._name = str(self.properties["Name"])
        return self._name

    @name.setter
    def name(self, value):
        if self._child_object:
            try:
                self.properties["Name"] = value
            except KeyError:
                self._app.logger.error("Name %s already assigned in the design", value)

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        """Retrieve arguments.

        Parameters
        ----------
        props :
            The default is ``None``.

        Returns
        -------
        list
            List of boundary properties.

        """
        if props is None:
            props = self.props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg

    @pyaedt_function_handler()
    def create(self):
        """Create a boundary.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.type == "Matrix":
            self._app.omaxwell_parameters.AssignMatrix(self._get_args())
        elif self.type == "Torque":
            self._app.omaxwell_parameters.AssignTorque(self._get_args())
        elif self.type == "Force":
            self._app.omaxwell_parameters.AssignForce(self._get_args())
        elif self.type == "LayoutForce":
            self._app.omaxwell_parameters.AssignLayoutForce(self._get_args())
        else:
            return False
        return self._initialize_tree_node()

    @pyaedt_function_handler()
    def update(self):
        """Update the boundary.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.type == "Matrix":
            self._app.omaxwell_parameters.EditMatrix(self.name, self._get_args())
        elif self.type == "Force":
            self._app.omaxwell_parameters.EditForce(self.name, self._get_args())
        elif self.type == "Torque":
            self._app.omaxwell_parameters.EditTorque(self.name, self._get_args())
        else:
            return False
        return True

    @pyaedt_function_handler()
    def _create_matrix_reduction(self, red_type, sources, matrix_name=None, join_name=None):
        if not self._app.solution_type == "EddyCurrent":
            self._app.logger.error("Matrix reduction is possible only in Eddy current solvers.")
            return False, False
        if not matrix_name:
            matrix_name = generate_unique_name("ReducedMatrix", n=3)
        if not join_name:
            join_name = generate_unique_name("Join" + red_type, n=3)
        try:
            self._app.omaxwell_parameters.AddReduceOp(
                self.name,
                matrix_name,
                ["NAME:" + join_name, "Type:=", "Join in " + red_type, "Sources:=", ",".join(sources)],
            )
            return matrix_name, join_name
        except Exception:
            self._app.logger.error("Failed to create Matrix Reduction")
            return False, False

    @pyaedt_function_handler()
    def join_series(self, sources, matrix_name=None, join_name=None):
        """Create matrix reduction by joining sources in series.

        Parameters
        ----------
        sources : list
            Sources to be included in matrix reduction.
        matrix_name :  str, optional
            Name of the string to create.
        join_name : str, optional
            Name of the Join operation.

        Returns
        -------
        (str, str)
            Matrix name and Joint name.

        """
        return self._create_matrix_reduction(
            red_type="Series", sources=sources, matrix_name=matrix_name, join_name=join_name
        )

    @pyaedt_function_handler()
    def join_parallel(self, sources, matrix_name=None, join_name=None):
        """Create matrix reduction by joining sources in parallel.

        Parameters
        ----------
        sources : list
            Sources to be included in matrix reduction.
        matrix_name :  str, optional
            Name of the matrix to create.
        join_name : str, optional
            Name of the Join operation.

        Returns
        -------
        (str, str)
            Matrix name and Joint name.

        """
        return self._create_matrix_reduction(
            red_type="Parallel", sources=sources, matrix_name=matrix_name, join_name=join_name
        )


class MaxwellMatrix(object):
    def __init__(self, app, parent_name, reduced_name):
        self._app = app
        self.parent_matrix = parent_name
        self.name = reduced_name
        self.__sources = None

    @property
    def sources(self):
        """List of matrix sources."""
        if self._app.solution_type == "EddyCurrent":
            sources = (
                self._app.odesign.GetChildObject("Parameters")
                .GetChildObject(self.parent_matrix)
                .GetChildObject(self.name)
                .GetChildNames()
            )
            self.__sources = {}
            for s in sources:
                excitations = (
                    self._app.odesign.GetChildObject("Parameters")
                    .GetChildObject(self.parent_matrix)
                    .GetChildObject(self.name)
                    .GetChildObject(s)
                    .GetPropValue("Source")
                )
                self.__sources[s] = excitations
        return self.__sources

    @pyaedt_function_handler()
    def update(self, old_source, source_type, new_source=None, new_excitations=None):
        """Update the reduced matrix.

        Parameters
        ----------
        old_source : str
            Original name of the source to update.
        source_type : str
            Source type, which can be ``Series`` or ``Parallel``.
        new_source : str, optional
            New name of the source to update.
            The default value is the old source name.
        new_excitations : str, optional
            List of excitations to include in the matrix reduction.
            The default values are excitations included in the source to update.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if old_source not in self.sources:
            self._app.logger.error("Source does not exist.")
            return False
        else:
            new_excitations = self.sources[old_source] if not new_excitations else new_excitations
        if source_type.lower() not in ["series", "parallel"]:
            self._app.logger.error("Join type not valid.")
            return False
        if not new_source:
            new_source = old_source
        args = ["NAME:" + new_source, "Type:=", "Join in " + source_type, "Sources:=", new_excitations]
        self._app.omaxwell_parameters.EditReduceOp(self.parent_matrix, self.name, old_source, args)
        return True

    @pyaedt_function_handler()
    def delete(self, source):
        """Delete a specified source in a reduced matrix.

        Parameters
        ----------
        source : string
            Name of the source to delete.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if source not in self.sources:
            self._app.logger.error("Invalid source name.")
            return False
        self._app.omaxwell_parameters.DeleteReduceOp(self.parent_matrix, self.name, source)
        return True
