AEDT post-processing
====================

AEDT offers a wide range of powerful post-processing tools for advanced data analysis and visualization.
PyAEDT provides dedicated classes that allow you to seamlessly interact with and modify these tools, expanding the scope of your data insights


.. note::
   Some functionalities are available only when AEDT is running
   in graphical mode.


Core
~~~~

The following classes grant access to the core post-processing functionalities of AEDT:

* **PostProcessor3D**: This class is utilized across all 3D applications, including HFSS, Maxwell 3D and 2D, Q3D Extractor, and Mechanical AEDT.

* **PostProcessorIcepak**: A specialized class for Icepak, which extends the ``PostProcessor3D`` class by adding features tailored to thermal analysis.

* **PostProcessorCircuit**: This class handles schematic post-processing, supporting Circuit and Twin Builder applications.

* **PostProcessor3DLayout**: A specialized class for HFSS 3D Layout, which extends the ``PostProcessor3D`` class.


.. currentmodule:: ansys.aedt.core.visualization.post.post_common_3d

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   PostProcessor3D


.. currentmodule:: ansys.aedt.core.visualization.post.post_icepak

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   PostProcessorIcepak


.. currentmodule:: ansys.aedt.core.visualization.post.post_circuit

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   PostProcessorCircuit


.. currentmodule:: ansys.aedt.core.visualization.post.post_3dlayout

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   PostProcessor3DLayout


You can access these classes directly from the design object:

.. code:: python

    from ansys.aedt.core import Hfss
    app = Hfss(specified_version="2023.1",
                 non_graphical=False, new_desktop_session=True,
                 close_on_exit=True, student_version=False)

    # This call returns the PostProcessor class
    post = app.post

    # This call returns a FieldPlot object
    plotf = post.create_fieldplot_volume(objects, quantity_name, setup_name, intrinsics)

    # This call returns a SolutionData object
    my_data = post.get_solution_data(expressions=trace_names)

    # This call returns a new standard report object and creates one or multiple reports from it.
    standard_report = post.reports_by_category.standard("db(S(1,1))")
    report_standard.create()
    sols = report_standard.get_solution_data()


User can get the properties of the default reports using the following class:

.. currentmodule:: ansys.aedt.core.visualization.post.common

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   Reports

.. code:: python

    from ansys.aedt.core import Hfss
    from ansys.aedt.core.visualization.post.common import Reports
    app = Hfss(specified_version="2024.2",
                 non_graphical=False, new_desktop_session=True,
                 close_on_exit=True, student_version=False)
    reports = Reports(app.post, app.design_type)
    app.release_desktop(False, False)


AEDT data is returned in a structured format, providing organized and detailed results.
For a comprehensive overview of the data structure and its capabilities, refer to the class definition below:


.. currentmodule:: ansys.aedt.core.visualization.post.solution_data

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   SolutionData


Field
~~~~~

AEDT offers additional specialized post-processing features for enhanced 3D field visualization and control.


The following classes manage all aspects of AEDT 3D post-processing and are utilized by the ``PostProcessor3D`` class:

.. currentmodule:: ansys.aedt.core.visualization.post.field_data

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   FieldPlot

.. code:: python

    from ansys.aedt.core import Hfss

    app = Hfss(specified_version="2024.2",
               non_graphical=False,
               new_desktop_session=False
               )
    test_points = [["0mm", "0mm", "0mm"], ["100mm", "20mm", "0mm"],
                   ["71mm", "71mm", "0mm"], ["0mm", "100mm", "0mm"]]
    p1 = app.modeler.create_polyline(test_points)
    setup = app.create_setup()

    report = app.post.create_fieldplot_line(quantity="Mag_E", assignment=p1.name)
    report.create()
    app.release_desktop(False, False)


Additionally, the following classes control field overlay settings,
enabling precise adjustments to visualization parameters:

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   ColorMapSettings
   AutoScale
   MinMaxScale
   Scale3DSettings
   NumberFormat
   MarkerSettings
   ArrowSettings
   FolderPlotSettings

The ``fields_calculator`` module includes the ``FieldsCalculator`` class.
It provides methods to interact with AEDT Fields Calculator by adding, loading and deleting custom expressions.

.. currentmodule:: ansys.aedt.core.visualization.post.fields_calculator

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   FieldsCalculator


HFSS
~~~~

For HFSS solutions, there are two additionally features: virtual ray tracing and farfield exporter.

To define and control virtual ray tracing (VRT) you can use:

.. currentmodule:: ansys.aedt.core.visualization.post.vrt_data

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   VRTFieldPlot


If you need to export HFSS far field data, then you can use the following feature to obtain the antenna metadata:

.. currentmodule:: ansys.aedt.core.visualization.post.farfield_exporter

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   FfdSolutionDataExporter

.. code:: python

    from ansys.aedt.core import Hfss

    app = Hfss()

    antenna_data = app.post.get_antenna_data()
    app.release_desktop(False, False)

If you need to export HFSS monostatic RCS data, then you can use the following feature to obtain the RCS metadata:

.. currentmodule:: ansys.aedt.core.visualization.post.rcs_exporter

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   MonostaticRCSExporter

.. code:: python

    from ansys.aedt.core import Hfss

    app = Hfss()

    rcs_data = app.post.get_rcs_data()
    app.release_desktop(False, False)


Icepak
~~~~~~

The ``monitor_icepak`` module includes the classes listed below to add, modify, and manage monitors during simulations.
Retrieve monitor values for post-processing and analysis to gain insights into key simulation metrics.
Methods and properties are accessible through the ``monitor`` property of the ``Icepak`` class.

.. currentmodule:: ansys.aedt.core.visualization.post.monitor_icepak

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   Monitor


The ``field_summary`` module includes the classes listed below to the ``Icepak`` field summary.

.. currentmodule:: ansys.aedt.core.visualization.post.field_summary

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   FieldSummary


Additional tools
~~~~~~~~~~~~~~~~

Finally, users can use additional AEDT postprocessing tools like SPiSim:

.. currentmodule:: ansys.aedt.core.visualization.post.spisim

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   SpiSim


.. currentmodule:: ansys.aedt.core.visualization.post.spisim_com_configuration_files.com_parameters

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   COMParameters
   COMParametersVer3p4


If you are looking for Virtual Compliance post processing, you should use this set of features:

.. currentmodule:: ansys.aedt.core.visualization.post.compliance

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   VirtualComplianceGenerator
   VirtualCompliance