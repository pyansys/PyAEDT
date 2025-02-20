Push excitation from file
=========================

The **push excitation from file** extension allows users to assign a time-domain excitation to a port in an HFSS design
by importing data from a file.

The extension provides a graphical user interface (GUI) for configuration,
or it can be used in batch mode via command line arguments.

The following image shows the extension GUI:

.. image:: ../../../_static/extensions/push_excitation.png
  :width: 800
  :alt: Push excitation UI


Features
--------

- Automatic detection and listing of available ports in the active HFSS design.
- Allow users to browse and select a time-domain excitation file.
- Validate file paths and port selections to ensure proper configuration.
- Supports both light and dark themes for the GUI.


Using the extension
--------------------

1. Open the **Automation** tab in the HFSS 3D Layout interface.
2. Locate and click the **push excitation from file** icon under the Extension Manager.
3. In the GUI, users can interact with the following elements:
   - **Port selection**: A dropdown menu to select the desired port from the HFSS design.
   - **File browser**: A text box and button to select the excitation file.
   - **Push excitation button**: A button to assign the excitation to the selected port.
   - **Theme toggle**: A button to switch between light and dark themes.
3. Click **Push excitation** after selecting the port and file to apply the configuration.


Command line
------------

The extension can also be used directly via the command line for batch processing.

Supported arguments include:

- **file_path**: Path to the excitation file.
- **choice**: Name of the port to assign the excitation.
- **is batch**: Boolean flag to enable batch mode.

Use the following syntax to run the extension:

.. toctree::
   :maxdepth: 2

   ../commandline
