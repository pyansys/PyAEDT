Import Nastran
==============

You can import a Nastran or STL file in any 3D modeler. You can also preview the imported file and decimate it prior to import.

You can access the extension from the icon created on the **Automation** tab using the Extension Manager.

The following image shows the extension user interface:

.. image:: ../../../_static/extensions/import_nastran_ui.png
  :width: 800
  :alt: Import Nastran UI


The available arguments are: ``file_path``, ``planar``, ``lightweight``, and ``decimate``.

By enabling ``lightweight`` check box the user imports the STL as a lightweight object.
The ``decimate`` parameter indicates the percentage of triangles that have to be removed during simplification.
A value of ``0.2`` means that 20% of the triangles is removed from the data read from the
file before importing in AEDT.
The ``planar`` parameter indicates that touching triangles that lie on the same plane are merged.

You can also launch the extension user interface from the terminal. An example can be found here:


.. toctree::
   :maxdepth: 2

   ../commandline