Create power map
================

The extension allows users to generate power maps for an Icepak design from a CSV file containing geometric
and source data.

The extension provides a graphical user interface (GUI) for configuration,
or it can be used in batch mode via command line arguments.

The following image shows the extension GUI:

.. image:: ../../../_static/extensions/power_map_ui.png
  :width: 800
  :alt: Create Power Map UI


Using the extension
-------------------

1. Open the **Automation** tab in the Icepak interface.
2. Locate and click the **Power Map from File** icon under the Extension Manager.
3. In the GUI, users can interact with the following elements:
   - **Browse file**: A button to open a file dialog and select the CSV file containing geometric and source data.
   - **Theme toggle**: A button to switch between light and dark themes for the UI.
   - **Create**: A button to initiate the power map creation process after selecting the CSV file.
4. Select the desired CSV file and click **Create** to generate the power maps.

Command line
------------

The extension can also be used directly via the command line for batch processing.

Supported arguments include:

- **file path**: The path to the CSV file that contains geometric and source data.
- **is batch**: Boolean flag to enable batch mode (set to `True` for batch processing).
- **is test**: Boolean flag to indicate if the operation is a test (set to `False` in production).

Use the following syntax to run the extension in batch mode:

.. toctree::
   :maxdepth: 2

   ../commandline

Example configuration file
--------------------------

Here is an example of a power map file:

:download:`CSV File example <../../../Resources/icepak_classic_powermap.csv>`
