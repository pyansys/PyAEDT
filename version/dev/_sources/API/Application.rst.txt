Application and solvers
=======================
The PyAEDT API includes classes for different applications available in Ansys Electronics Desktop (AEDT).
You must initialize AEDT to get access to all PyAEDT modules and methods.

.. image:: ../Resources/aedt_2.png
  :width: 800
  :alt: Ansys Electronics Desktop (AEDT) is a platform that enables true electronics system design.


Available PyAEDT apps are:

.. autosummary::
   :toctree: _autosummary

   ansys.aedt.core.desktop.Desktop
   ansys.aedt.core.hfss.Hfss
   ansys.aedt.core.q3d.Q3d
   ansys.aedt.core.q3d.Q2d
   ansys.aedt.core.maxwell.Maxwell2d
   ansys.aedt.core.maxwell.Maxwell3d
   ansys.aedt.core.icepak.Icepak
   ansys.aedt.core.hfss3dlayout.Hfss3dLayout
   ansys.aedt.core.mechanical.Mechanical
   ansys.aedt.core.rmxprt.Rmxprt
   ansys.aedt.core.circuit.Circuit
   ansys.aedt.core.maxwellcircuit.MaxwellCircuit
   ansys.aedt.core.emit.Emit
   ansys.aedt.core.twinbuilder.TwinBuilder

All other classes and methods are inherited into the app class.
AEDT, which is also referred to as the desktop app, is implicitly launched in any PyAEDT app.
Before accessing a PyAEDT app, the desktop app must be launched and initialized.
The desktop app can be explicitly or implicitly initialized as in the following examples.

Example with ``Desktop`` class explicit initialization:

.. code:: python

    from ansys.aedt.core import launch_desktop, Circuit
    d = launch_desktop(specified_version="2025.1",
                       non_graphical=False,
                       new_desktop_session=True,
                       close_on_exit=True,
                       student_version=False):
     circuit = Circuit()
     ...
     # Any error here will be caught by Desktop.
     ...
     d.release_desktop()

Example with ``Desktop`` class implicit initialization:

.. code:: python

    from ansys.aedt.core import Circuit
    circuit = Circuit(specified_version="2025.1",
                      non_graphical=False,
                      new_desktop_session=True,
                      close_on_exit=True,
                      student_version=False):
     circuit = Circuit()
     ...
     # Any error here will be caught by Desktop.
     ...
     circuit.release_desktop()


