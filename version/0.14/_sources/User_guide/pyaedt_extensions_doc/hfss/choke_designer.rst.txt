Choke designer
==============

The **Choke designer** extension enables users to create and customize choke configurations and export the generated
geometry to HFSS.

The extension provides a graphical user interface (GUI) for configuration,
or it can be used in batch mode via command line arguments.

The following image shows the extension GUI:

.. image:: ../../../_static/extensions/choke_designer_ui.png
  :width: 800
  :alt: Choke Designer GUI


Features
--------

- Configure choke parameters including core dimensions, windings, layers, and material properties.
- Export designs to HFSS.
- Save and load configurations as JSON files.
- Switch between light and dark themes in the GUI.


Using the extension
-------------------

1. Open the **Automation** tab in the HFSS interface.
2. Locate and click the **Choke designer** icon under the Extension Manager.
3. In the GUI, users can interact with the following options:
   - Adjust configuration parameters in the **Left panel** using radio buttons for options such as number of windings and layer types.
   - Modify detailed parameters for the core and windings in the **Right Panel** under respective tabs.
   - Use the buttons at the bottom to:
     - Save the current configuration as a `.json` file.
     - Load an existing configuration file.
     - Export to HFSS.
     - Toggle between light and dark themes.
4. Click on **Export to HFSS** to export design to HFSS.

.. note::

   Remember to check that your parameters are valid before exporting.


Command line
------------

The extension can also be used directly via the command line for batch processing.


Use the following syntax to run the extension:

.. toctree::
   :maxdepth: 2

   ../commandline


Example configuration file
--------------------------

Here is an example of a choke configuration in JSON format: :ref:`choke-file`.

Ensure the parameters are valid before importing.


Validation rules
----------------

- The outer radius must be greater than the inner radius for the core and windings.
- Heights and wire diameters must be positive.

The user interface provides detailed feedback on validation errors in the form of message boxes.
