Modeler in  HFSS 3D Layout
==========================

This section lists the core AEDT Modeler modules available in HFSS 3D Layout:

* Modeler
* Primitives
* Objects

They are accessible through the ``modeler`` module and ``modeler.objects`` property:

.. code:: python

    from ansys.aedt.core import Hfss3dLayout
    hfss = Hfss3dLayout()
    my_modeler = hfss.modeler

    ...


Modeler
~~~~~~~

The ``Modeler`` module contains all properties and methods needed to edit a
modeler, including all primitives methods and properties:


* ``Modeler3DLayout`` for HFSS 3D Layout



.. currentmodule:: ansys.aedt.core.modeler

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   modeler_pcb.Modeler3DLayout


Objects in HFSS 3D Layout
~~~~~~~~~~~~~~~~~~~~~~~~~
The following classes define the object properties for HFSS 3D Layout.
They contain all getters and setters to simplify object manipulation.

.. currentmodule:: ansys.aedt.core.modeler.pcb

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   object_3d_layout.Components3DLayout
   object_3d_layout.Nets3DLayout
   object_3d_layout.Pins3DLayout
   object_3d_layout.Line3dLayout
   object_3d_layout.Polygons3DLayout
   object_3d_layout.Circle3dLayout
   object_3d_layout.Rect3dLayout
   object_3d_layout.Points3dLayout
   object_3d_layout.Padstack

.. code:: python

    from ansys.aedt.core import Hfss3dLayout
    app = Hfss3dLayout(specified_version="2025.1",
               non_graphical=False, new_desktop_session=True,
               close_on_exit=True, student_version=False)

    # This call returns the Modeler3DLayout class
    modeler = app.modeler

    # This call returns a Primitives3D object
    primitives = modeler

    # This call returns an Object3d object
    my_rect = primitives.create_rectangle([0,0,0],[10,10])

    # Getter and setter
    my_rect.material_name

    ...
