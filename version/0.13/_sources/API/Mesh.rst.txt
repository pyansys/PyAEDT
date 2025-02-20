Mesh operations
===============
The ``Mesh`` module includes these classes:

* ``Mesh`` for HFSS, Maxwell 2D, Maxwell 3D, Q2D Extractor, and Q3D Extractor
* ``IcepakMesh`` for Icepak
* ``Mesh3d`` for HFSS 3D Layout

They are accessible through the mesh property:

.. currentmodule:: ansys.aedt.core.modules

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   mesh.Mesh
   mesh_icepak.IcepakMesh
   mesh_3d_layout.Mesh3d

.. code:: python

    from ansys.aedt.core import Maxwell3d
    app = Maxwell3d(specified_version="2023.1",
                 non_graphical=False, new_desktop_session=True,
                 close_on_exit=True, student_version=False)
    # This call returns the Mesh class
    my_mesh = app.mesh
    # This call executes a ``Mesh`` method and creates an object to control the mesh operation
    mesh_operation_object = my_mesh.assign_surface_mesh("MyBox", 2)
    ...

Icepak mesh
~~~~~~~~~~~~~~~

These objects are relevant objects while using the ``MeshIcepak`` class:

.. currentmodule:: ansys.aedt.core.modules.mesh_icepak

.. autosummary::
   :toctree: _autosummary
   :nosignatures:


   Region
   SubRegion
   MeshRegion
   GlobalMeshRegion