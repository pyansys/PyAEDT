Variable
========
This module provides all functionalities for creating and editing
design and project variables in the 3D tools.

.. code:: python

    from ansys.aedt.core import Hfss
    app = Hfss(specified_version="2025.1",
                 non_graphical=False, new_desktop_session=True,
                 close_on_exit=True, student_version=False)

    # This call returns the VariableManager class
    variable_manager = self.aedtapp._variable_manager

    # Set and get a variable
    app["w"] = "10mm"
    a = app["w"]
    ...


.. currentmodule:: ansys.aedt.core.application.variables

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   VariableManager
   Variable
   DataSet
   CSVDataset



Quantity and numbers
====================

Quantities with units can be managed using the class Quantity.

.. code:: python

    from ansys.aedt.core.generic.numbers import Quantity
    a = Quantity(1, "GHz")
    b = a + 1
    c = a + "1MHz"
    d = a + b
    a.unit = "Hz"
    e = a.to("MHz")
    str(a)
    float(a)
    hfss = ansys.aedt.core.Hfss()
    setup = hfss.create_setup()
    setup.props["Freq"] = a


.. currentmodule:: ansys.aedt.core.generic.numbers

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   Quantity

