Primitives
==========

This section lists the core AEDT Modeler primitives that are supported both in 2D and 3D solvers (HFSS, Maxwell,
Icepak, Q3D, and Mechanical):

* Primitives
* Objects

They are accessible through the ``modeler.objects`` property:

.. code:: python

    from pyaedt import Hfss
    app = Hfss(specified_version="2022.2",
                 non_graphical=False, new_desktop_session=True,
                 close_on_exit=True, student_version=False)

    # This call return the Modeler3D class
    modeler = app.modeler

    # This call returns a Primitives3D object
    primitives = modeler

    # This call return an Object3d object
    my_box = primitives.create_box([0,0,0],[10,10,10])
    my_box = primitives.objects[my_box.id]

    # This call return a FacePrimitive object list
    my_box.faces
    # This call returns an EdgePrimitive object list
    my_box.edges
    my_box.faces[0].edges

    # This call returns a VertexPrimitive object list
    my_box.vertices
    my_box.faces[0].vertices
    my_box.faces[0].edges[0].vertices

    ...



Objects
~~~~~~~

The following classes define objects properties for 3D and 2D Solvers (excluding HFSS 3D Layout).
They contain all getters and setters to simplify object manipulation.



.. currentmodule:: pyaedt.modeler

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   cad.object3d.Object3d
   cad.elements3d.FacePrimitive
   cad.elements3d.EdgePrimitive
   cad.elements3d.VertexPrimitive
   cad.polylines.PolylineSegment
   cad.polylines.Polyline
   cad.components_3d.UserDefinedComponent
   cad.elements3d.Point
   cad.elements3d.Plane
   cad.elements3d.HistoryProps
   cad.elements3d.BinaryTreeNode


.. code:: python

    from pyaedt import Hfss
    app = Hfss(specified_version="2022.2",
               non_graphical=False, new_desktop_session=True,
               close_on_exit=True, student_version=False)

    # This call returns the Modeler3D class
    modeler = app.modeler

    # This call returns a Primitives3D object
    primitives = modeler

    # This call returns an Object3d object
    my_box = primitives.create_box([0,0,0],[10,10,10])

    # Getter and setter
    my_box.material_name
    my_box.material_name = "copper"

    my_box.faces[0].center

    ...


Coordinate systems and geometry operators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This module contains all properties and methods needed to edit a
coordinate system and a set of useful geometry operators.
The ``CoordinateSystem`` class is accessible through the ``create_coordinate_system``
method or the ``coordinate_systems`` list. The ``GeometryOperators`` class can be
imported and used because it is made by static methods.


.. currentmodule:: pyaedt.modeler

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   cad.Modeler.CoordinateSystem
   geometry_operators.GeometryOperators


.. code:: python

    from pyaedt import Hfss
    app = Hfss(specified_version="2022.2",
                 non_graphical=False, new_desktop_session=True,
                 close_on_exit=True, student_version=False)

    # This call returns the CoordinateSystem object list
    cs = app.modeler.coordinate_systems

    # This call returns a CoordinateSystem object
    new_cs = app.modeler.create_coordinate_system()

    ...


Advanced modeler operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~

PyAEDT includes some advanced modeler tools like ``MultiPartComponent`` for 3D component
management and ``Stackup3D`` for parametric creation of 3D modeler stackups.

.. toctree::
   :maxdepth: 2

   MultiPartComponent
   Stackup3D