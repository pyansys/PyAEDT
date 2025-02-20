Extension manager
=================

Extensions provide a simplified interface to perform automated workflows in AEDT, they are generally tool-specific and are therefore only accessible given the appropriate context.
In AEDT, you can use the `Extension manager <https://aedt.docs.pyansys.com/version/stable/Getting_started/Installation.html#extension-manager>`_ to add or remove extensions.
The Extension manager allows the user to install three different types of extensions:

- **Pre-installed extensions** available at project level.
- **Open source PyAEDT toolkits** available at application level.
- **Custom extensions** installable both at project and application level.

The following sections provide further clarification.

You can launch extensions in standalone mode from the console or a Python script.

Pre-installed extensions
------------------------

Project extensions
~~~~~~~~~~~~~~~~~~

Pre-installed extensions are available at project level so they are available for all AEDT applications.
They are small automated workflow with a simple UI.

.. grid:: 2

   .. grid-item-card:: Import Nastran
            :link: pyaedt_extensions_doc/project/import_nastran
            :link-type: doc
            :margin: 2 2 0 0

            Import a Nastran or STL file in any 3D modeler application.


   .. grid-item-card:: Configure Layout
            :link: pyaedt_extensions_doc/project/configure_edb
            :link-type: doc
            :margin: 2 2 0 0

            Configure layout for PCB & package analysis.


   .. grid-item-card:: Advanced Fields Calculator
            :link: pyaedt_extensions_doc/project/advanced_fields_calculator
            :link-type: doc
            :margin: 2 2 0 0

            Lear how to use the Advanced Fields Calculator extension.


   .. grid-item-card:: Kernel converter
            :link: pyaedt_extensions_doc/project/kernel_convert
            :link-type: doc
            :margin: 2 2 0 0

            Lear how to convert projects from 2022R2 to newer versions.


HFSS 3D Layout extensions
~~~~~~~~~~~~~~~~~~~~~~~~~

Pre-installed extensions are available at HFSS 3D Layout level.
They are small automated workflow with a simple UI.

.. grid:: 2

   .. grid-item-card:: Parametrize Layout
            :link: pyaedt_extensions_doc/hfss3dlayout/parametrize_edb
            :link-type: doc
            :margin: 2 2 0 0

            Parametrize a full layout design.


   .. grid-item-card:: Generate arbitrary wave ports
            :link: pyaedt_extensions_doc/hfss3dlayout/arbitrary_wave_port
            :link-type: doc
            :margin: 2 2 0 0

            Generate arbitrary wave ports in HFSS.


HFSS extensions
~~~~~~~~~~~~~~~

Pre-installed extensions are available at HFSS level.
They are small automated workflow with a simple UI.

.. grid:: 2

   .. grid-item-card:: Choke designer
            :link: pyaedt_extensions_doc/hfss/choke_designer
            :link-type: doc
            :margin: 2 2 0 0

            Design a choke and import it in HFSS.


Icepak extensions
~~~~~~~~~~~~~~~~~

Pre-installed extensions are available at Icepak level.
They are small automated workflow with a simple UI.

.. grid:: 2

   .. grid-item-card:: Create power map
            :link: pyaedt_extensions_doc/icepak/create_power_map
            :link-type: doc
            :margin: 2 2 0 0

            Import a CSV file containing sources layout and power dissipation information.


.. toctree::
   :hidden:
   :maxdepth: 1

   pyaedt_extensions_doc/project/index
   pyaedt_extensions_doc/hfss3dlayout/index
   pyaedt_extensions_doc/hfss/index
   pyaedt_extensions_doc/icepak/index


Open source toolkits
--------------------

Open source toolkits are available at application level.
They are advanced workflows where backend and frontend are split.
They are also fully documented and tested.

Here are some links to existing toolkits:
- Hfss: `Antenna Wizard <https://github.com/ansys/pyaedt-toolkits-antenna>`_.
- Maxwell 3D: `Magnet Segmentation Wizard <https://github.com/ansys/magnet-segmentation-toolkit>`_.


Custom extensions
-----------------

Custom extensions are custom workflows (Python script) that can be installed both at project and application level.
From the Extension manager select the target destination:

.. image:: ../Resources/toolkit_manager_1.png
  :width: 500
  :alt: PyAEDT toolkit manager 1

Select `Custom` as the extension type.
Provide the path of the Python script containing the workflow.
Enter the extension name. This is the name that appears beneath the button in the Automation tab after a successful installation.

.. image:: ../Resources/my_custom_extension.png
  :width: 500
  :alt: Custom Extension

After the normal completion of the installation a new button appears:

.. image:: ../Resources/my_custom_extension_1.png
  :width: 500
  :alt: Custom Extension 1

The example below is a simple example of custom extension.
The Python script requires a common initial part to define the port and the version of the AEDT session to connect to.

.. code:: python

    import ansys.aedt.core
    import os

    # common part
    if "PYAEDT_SCRIPT_PORT" in os.environ and "PYAEDT_SCRIPT_VERSION" in os.environ:
        port = os.environ["PYAEDT_SCRIPT_PORT"]
        version = os.environ["PYAEDT_SCRIPT_VERSION"]
    else:
        port = 0
        version = "2024.2"

    # your pyaedt script
    app = ansys.aedt.core.Desktop(new_desktop_session=False, specified_version=version, port=port)

    active_project = app.active_project()
    active_design = app.active_design(active_project)

    # no need to hardcode you application but get_pyaedt_app will detect it for you
    aedtapp = ansys.aedt.core.get_pyaedt_app(design_name=active_design.GetName(), desktop=app)

    # your workflow
    aedtapp.modeler.create_sphere([0, 0, 0], 20)

    app.release_desktop(False, False)
