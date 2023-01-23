Components, primitives, and nets
================================
These classes are the containers of components, primitives, nets, and all relative methods.
Primitives are planes, lines, rectangles, and circles.


.. code:: python

    from pyaedt import Edb
    edb = Edb(myedb, edbversion="2022.2")

    comp = edb.core_components.get_component_by_name("J1")

    signalnets = edbcore_nets.signal_nets
    powernets = edb.core_nets.power_nets
    ...



.. currentmodule:: pyaedt.edb_core.edb_data

.. autosummary::
   :toctree: _autosummary
   :nosignatures:


   components_data.EDBComponent
   components_data.EDBComponentDef
   nets_data.EDBNetsData
   primitives_data.EDBPrimitives
   primitives_data.EDBArcs
