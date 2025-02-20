Boundary objects
================
This section lists classes for creating and editing
boundaries in the 3D tools. These objects are returned by
app methods and can be used to edit or delete a boundary condition.


.. currentmodule:: ansys.aedt.core.modules.boundary

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   common.BoundaryObject
   hfss_boundary.FarFieldSetup
   hfss_boundary.NearFieldSetup
   q3d_boundary.Matrix
   maxwell_boundary.MaxwellParameters
   maxwell_boundary.MaxwellMatrix
   layout_boundary.BoundaryObject3dLayout
   icepak_boundary.NetworkObject

Circuit excitations
-------------------
To facilitate excitations assignment in Circuit, multiple classes have been created.

.. currentmodule:: ansys.aedt.core.modules.boundary.circuit_boundary

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   Sources
   PowerSinSource
   PowerIQSource
   VoltageFrequencyDependentSource
   VoltageDCSource
   VoltageSinSource
   CurrentSinSource
   Excitations

Native components
-----------------

When native components object are created, the ``NativeComponentObject`` class is returned. For PCB components, ``NativeComponentPCB`` is returned.

.. currentmodule:: ansys.aedt.core.modules.boundary.layout_boundary

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   NativeComponentPCB
   NativeComponentObject
   PCBSettingsDeviceParts
   PCBSettingsPackageParts

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

.. currentmodule:: ansys.aedt.core.modules.boundary.icepak_boundary

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   SinusoidalDictionary
   LinearDictionary
   PowerLawDictionary
   ExponentialDictionary
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