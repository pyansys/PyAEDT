Advanced fields calculator
==========================

The Advanced Fields Calculator provides an additional pool of custom expressions appropriate for each solver.
These expressions can be used with the ones already available in the AEDT Fields Calculator.
These two libraries combined together provide a way to conveniently calculate frequently used quantities.

Operations such as adding, loading, and deleting named expressions and creating CLC expressions files are now
automated and available in PyAEDT.

The core component is a TOML file (``expression_catalog.toml``) that functions as an expressions catalog.
It is located in the ``misc`` directory of the codebase and looks like this:

  .. image:: ../../../_static/extensions/expressions_catalog.png
    :width: 800
    :alt: Expressions catalog

- ``Description``: Name to display in the UI.

  .. image:: ../../../_static/extensions/advanced_fields_calc_1.png
    :width: 800
    :alt: Advanced Fields Calculator

- ``Operations``: List of operations to perform to compute the expression.

Expressions tend to be classified as either *general* or *non-general*.

General expressions are generally independent of a geometry definition.
For example, in the previous image, to calculate the magnetic field tangential component, there is no need to specify a
geometry assignment.
Whereas in the following example, to calculate the voltage drop along a line, the line assignment is needed for the computation:

.. image:: ../../../_static/extensions/voltage_drop_line.png
  :width: 800
  :alt: Voltage drop line

To help you understand this difference, a method named ``is_general_expression(expression_name)`` is implemented.
This method returns ``True`` if the expression is general or ``False`` otherwise.

It is possible to add named expressions dependent to one another:

.. image:: ../../../_static/extensions/tang_stress_tensor.png
  :width: 800
  :alt: Tangential stress tensor

It is also possible for you to add an external TOML file in the ``PersonalLib`` folder
to load custom expressions. This could be especially useful if you do not want to share expressions.
To load a personalized TOML file, use the ``load_expression_file(toml_file_path)`` method.

Finally, this code shows how you can use the Advanced Field Calculator:

.. code:: python

    import ansys.aedt.core
    hfss = ansys.aedt.core.Hfss()

    # Specify the AEDT session to connect
    os.environ["PYAEDT_SCRIPT_PORT"] = str(hfss.desktop_class.port)
    os.environ["PYAEDT_SCRIPT_VERSION"] = hfss.desktop_class.aedt_version_id

    # Add an existing expression in the catalog
    name = hfss.post.fields_calculator.add_expression("voltage_line", "Polyline1")

    # Create plots in AEDT specified in the .toml
    hfss.post.fields_calculator.expression_plot("voltage_line", "Polyline1", [name])

    # Delete expression
    hfss.post.fields_calculator.delete_expression(name)

    hfss.release_desktop(False, False)