Q3D templates and arguments
===========================


This section lists all setup templates with their default values and keys available in Q3D and 2D Extractor.
Note that to use nested parameters, you can set a parameter using the "__" separator as shown in the following example.

You can edit a setup after it is created. Here is an example:

.. code:: python


    from ansys.aedt.core import Q3d

    app = Q3d()
    # Any property of this setup can be found on this page.
    setup = app.create_setup(AC__MaxPasses=6)



.. pprint:: ansys.aedt.core.modules.setup_templates.Matrix
.. pprint:: ansys.aedt.core.modules.setup_templates.Close
.. pprint:: ansys.aedt.core.modules.setup_templates.Open

