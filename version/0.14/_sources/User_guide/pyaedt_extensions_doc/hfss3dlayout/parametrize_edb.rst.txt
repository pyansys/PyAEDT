Parametrize Layout
==================

The extension allows users to apply parametrization to layouts in HFSS 3D Layout designs.
This includes layers, materials, padstacks, traces, and nets, providing a flexible way to create parametric models.

The extension provides a graphical user interface (GUI) for configuration,
or it can be used in batch mode via command line arguments.

The following image shows the extension user interface:

.. image:: ../../../_static/extensions/parametrize.png
  :width: 800
  :alt: Parametrize Layout UI


Features
--------

- Allow users to parametrize layers, materials, padstacks, nets, and traces, with support for relative and absolute parameters.
- Support the expansion of polygons and voids by a specified amount (in mm).


Using the extension
-------------------

1. Open the **Automation** tab in the HFSS 3D Layout interface.
2. Locate and click the **Layout Parametrization** icon under the Extension Manager.
3. In the GUI, users can interact with the following elements:
   - **Project Name**: A text box to specify the name for the new parametric project.
   - **Use Relative Parameters**: A checkbox to enable or disable relative parameters for the design.
   - **Parametrize Layers**: A checkbox to enable parametrization of layers in the layout.
   - **Parametrize Materials**: A checkbox to enable parametrization of materials.
   - **Parametrize Padstacks**: A checkbox to enable parametrization of padstacks.
   - **Parametrize Traces**: A checkbox to enable parametrization of traces.
   - **Extend Polygons (mm)**: A text box to define the expansion size for polygons in mm.
   - **Extend Voids (mm)**: A text box to define the expansion size for voids in mm.
   - **Select Nets**: A list box to select nets (or leave empty for all nets) that is parametrized.
4. Select the desired options and click **Create Parametric Model** to generate the parametric model.


Command line
------------

Supported arguments include:

- **aedb path**: Path to the input AEDB file.
- **design name**: Name of the design in the AEDB file.
- **parametrize layers**: Boolean flag to enable parametrization of layers.
- **parametrize materials**: Boolean flag to enable parametrization of materials.
- **parametrize padstacks**: Boolean flag to enable parametrization of padstacks.
- **parametrize traces**: Boolean flag to enable parametrization of traces.
- **nets filter**: List of nets to apply parametrization to (leave empty for all nets).
- **expansion polygon mm**: Expansion size for polygons in mm.
- **expansion void mm**: Expansion size for voids in mm.
- **relative parametric**: Boolean flag to apply relative parameters.
- **project name**: Name for the new parametric project.
- **is batch**: Boolean flag to enable batch mode.

Use the following syntax to run the extension:

.. toctree::
   :maxdepth: 2

   ../commandline
