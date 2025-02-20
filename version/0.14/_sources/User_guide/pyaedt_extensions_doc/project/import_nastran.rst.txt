Import Nastran
==============

The extension allows users to import Nastran or STL files into AEDT.

The extension provides a graphical user interface (GUI) for configuration,
or it can be used in batch mode via command line arguments.

The following image shows the extension GUI:

.. image:: ../../../_static/extensions/import_nastran_ui.png
  :width: 800
  :alt: Import Nastran UI


Features
--------

- Import Nastran or STL files into AEDT.
- Configure the import process with options such as:
  - Decimation factor for mesh reduction.
  - Import as lightweight geometry (only for HFSS).
  - Planar merging for geometry simplification.
- Preview the geometry before final import.
- Switch between light and dark themes in the GUI.


Using the extension
--------------------

1. Open the **Automation** tab.
2. Locate and click the **Import Nastran or STL File** icon under the Extension Manager.
3. In the user interface:
   - Select a NAS or STL file using the **Browse** button.
   - Set the **Decimation factor** to control the level of mesh reduction.
   - Enable **Lightweight Import** to import the geometry as lightweight (HFSS only).
   - Enable **Planar Merge** to simplify planar surfaces in the geometry.
   - Use the **Preview** button to preview the geometry before importing.
4. To import the geometry into AEDT, click **OK**. Ensure that the settings are correct before finalizing the import.

Command line
------------

The extension can also be used directly via the command line for batch processing.

Supported arguments include:

- **file_path**: Specifies the path to the Nastran or STL file to be imported.
- **lightweight**: Specifies whether to import the geometry as lightweight (True/False).
- **decimate**: Specifies the decimation factor for mesh reduction (float).
- **planar**: Specifies whether to enable planar merging (True/False).

Use the following syntax to run the extension:

.. toctree::
   :maxdepth: 2

   ../commandline
