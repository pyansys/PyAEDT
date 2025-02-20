Parametrize Layout
==================

You can parametrize stackup, materials, padstacks and traces of an existing 3D Layout design and also
and change the size of voids and polygons to conduct corner analysis.

The extension is accessible through the icon created by the Extension Manager in the **Automation** tab.

The following image shows the extension user interface:

.. image:: ../../../_static/extensions/parametrize.png
  :width: 800
  :alt: Parametrize Layout UI


The available arguments are: ``aedb_path``, ``design_name``, ``parametrize_layers``,
``parametrize_materials``, ``parametrize_padstacks``, ``parametrize_traces``, ``nets_filter``,
``expansion_polygon_mm``, ``expansion_void_mm``, ``relative_parametric``, ``project_name``.

``aedb_path`` and ``design_name`` define the source aedb project.
``parametrize_layers``, ``parametrize_materials``, ``parametrize_padstacks``, ``parametrize_traces``
define which part of the aedb has to be parametrized while the ``nets_filter`` defines which net has to be included.
``expansion_polygon_mm`` and ``expansion_void_mm`` define if and which value of expansion has to be applied on
polygons and voids.
``relative_parametric`` defines if the parameters have to be considered as a delta of the original value.
``project_name`` is the new project name.

The extension user interface can also be launched from the terminal. An example can be found here:


.. toctree::
   :maxdepth: 2

   ../commandline
