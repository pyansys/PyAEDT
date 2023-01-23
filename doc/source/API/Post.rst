Postprocessing
==============
This section lists modules for creating and editing
plots in AEDT. They are accessible through the ``post`` property.

.. note::
   Some capabilities of the ``AdvancedPostProcessing`` module require Python 3 and
   installations of the `numpy <https://numpy.org/doc/stable/>`_,
   `matplotlib <https://matplotlib.org/>`_, and `pyvista <https://docs.pyvista.org/>`_ 
   packages.

.. note::
   Some functionalities are available only when AEDT is running 
   in graphical mode.


.. currentmodule:: pyaedt.modules

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   AdvancedPostProcessing.PostProcessor
   solutions.SolutionData
   solutions.FieldPlot
   solutions.FfdSolutionData


.. code:: python

    from pyaedt import Hfss
    app = Hfss(specified_version="2022.2",
                 non_graphical=False, new_desktop_session=True,
                 close_on_exit=True, student_version=False)

    # This call return the PostProcessor class
    post = app.post

    # This call return a FieldPlot object
    plotf = post.create_fieldplot_volume(object_list, quantityname, setup_name, intrinsic_dict)

    # This call return a SolutionData object
    my_data = post.get_report_data(expression=trace_names)

    # This call returns a new standard report object and creates one or multiple reports from it.
    standard_report = post.report_by_category.standard("db(S(1,1))")
    standard_report.create()
    sols = standard_report.get_solution_data()
    ...


AEDT report management
~~~~~~~~~~~~~~~~~~~~~~
AEDT provides great flexibility in reports.
PyAEDT has classes for manipulating any report property.


.. note::
   Some functionalities are available only when AEDT is running
   in graphical mode.


.. currentmodule:: pyaedt.modules

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   report_templates.Trace
   report_templates.LimitLine
   report_templates.Standard
   report_templates.Fields
   report_templates.NearField
   report_templates.FarField
   report_templates.EyeDiagram
   report_templates.Emission
   report_templates.Spectral


Plot fields and data outside AEDT
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
PyAEDT supports external report capabilities available with installed third-party
packages like `numpy <https://numpy.org/doc/stable/>`_,
`pandas <https://pandas.pydata.org/>`_, `matplotlib <https://matplotlib.org/>`_,
and `pyvista <https://docs.pyvista.org/>`_.

.. currentmodule:: pyaedt.modules

.. autosummary::
   :toctree: _autosummary
   :nosignatures:


   solutions.SolutionData
   solutions.FieldPlot
   solutions.FfdSolutionData
   AdvancedPostProcessing.ModelPlotter


Icepak monitors
~~~~~~~~~~~~~~~

.. currentmodule:: pyaedt.modules.monitor_icepak

.. autosummary::
   :toctree: _autosummary
   :nosignatures:


   FaceMonitor
   PointMonitor
   Monitor