Boundary objects
================
This section lists classes for creating and editing
boundaries in the 3D tools. These objects are returned by
app methods and can be used to edit or delete a boundary condition.


.. currentmodule:: ansys.aedt.core.modules.boundary

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   BoundaryObject
   BoundaryObject3dLayout
   NetworkObject
   FarFieldSetup
   Matrix
   BoundaryObject3dLayout
   Sources
   Excitations

Native components
-----------------

When native components object are created, the ``NativeComponentObject`` class is returned. For PCB components, ``NativeComponentPCB`` is returned.

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   NativeComponentObject
   NativeComponentPCB

``Native Component Object`` example:

.. code:: python

    from ansys.aedt.core import Icepak
    ipk = Icepak()
    component_name = "RadioBoard1"
    pcb_comp = self.aedtapp.create_ipk_3dcomponent_pcb(
        component_name, link_data, solution_freq, resolution, custom_x_resolution=400, custom_y_resolution=500
    )
     # pcb_comp is a NativeComponentPCB
    ...
    ipk.release_desktop()

Icepak transient assignments
----------------------------
To facilitate transient assignment handling in Icepak, it is possible to use one of the following classes:

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   LinearDictionary
   PowerLawDictionary
   ExponentialDictionary
   SinusoidalDictionary
   SquareWaveDictionary
   PieceWiseLinearDictionary

It is possible to initialize the class manually or through a method:

.. code:: python

    bc_transient = ipk.create_sinusoidal_transient_assignment(vertical_offset="1W", vertical_scaling="3",
                                                                  period="2", period_offset="0.5s")
    # bc_transient will be SinusoidalDictionary type
    ipk.assign_solid_block("Cylinder1", bc_transient)

    #or

    bc_transient = SinusoidalDictionary(vertical_offset="1W", vertical_scaling="3",
                                            period="2", period_offset="0.5s")
    ipk.assign_solid_block("Cylinder1", bc_transient)