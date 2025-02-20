Advanced
========

You can use PyAEDT for postprocessing of AEDT results to display graphics object and plot data.


Touchstone
~~~~~~~~~~

TouchstoneData class is based on `scikit-rf <https://scikit-rf.readthedocs.io/en/latest/>`_ package and allows advanced
touchstone post-processing.
The following methods allows to read and check touchstone files.

.. currentmodule:: ansys.aedt.core.visualization.advanced.touchstone_parser

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   TouchstoneData.get_insertion_loss_index
   TouchstoneData.plot_insertion_losses
   TouchstoneData.plot
   TouchstoneData.plot_return_losses
   TouchstoneData.get_mixed_mode_touchstone_data
   TouchstoneData.get_return_loss_index
   TouchstoneData.get_insertion_loss_index_from_prefix
   TouchstoneData.get_next_xtalk_index
   TouchstoneData.get_fext_xtalk_index_from_prefix
   TouchstoneData.plot_next_xtalk_losses
   TouchstoneData.plot_fext_xtalk_losses
   TouchstoneData.get_worst_curve
   read_touchstone
   check_touchstone_files
   find_touchstone_files


Here an example on how to use TouchstoneData class.

.. code:: python

    from ansys.aedt.core.visualization.advanced.touchstone_parser import TouchstoneData

    ts1 = TouchstoneData(touchstone_file=os.path.join(test_T44_dir, "port_order_1234.s8p"))
    assert ts1.get_mixed_mode_touchstone_data()
    ts2 = TouchstoneData(touchstone_file=os.path.join(test_T44_dir, "port_order_1324.s8p"))
    assert ts2.get_mixed_mode_touchstone_data(port_ordering="1324")

    assert ts1.plot_insertion_losses(plot=False)
    assert ts1.get_worst_curve(curve_list=ts1.get_return_loss_index(), plot=False)


Farfield
~~~~~~~~

PyAEDT offers sophisticated tools for advanced farfield post-processing.
There are two complementary classes: ``FfdSolutionDataExporter`` and ``FfdSolutionData``.

- FfdSolutionDataExporter: Enables efficient export and manipulation of farfield data. It allows users to convert simulation results into a standard metadata format for further analysis, or reporting.

- FfdSolutionData: Focuses on the direct access and processing of farfield solution data. It supports a comprehensive set of postprocessing operations, from visualizing radiation patterns to computing key performance metrics.


.. currentmodule:: ansys.aedt.core.visualization.advanced.farfield_visualization

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   FfdSolutionData


This code shows how you can get the farfield data and perform some post-processing:

.. code:: python

    import ansys.aedt.core
    from ansys.aedt.core.generic.farfield_visualization import FfdSolutionDataExporter
    app = ansys.aedt.core.Hfss()
    ffdata = app.get_antenna_data(frequencies=None,
                                  setup="Setup1 : Sweep",
                                  sphere="3D",
                                  variations=None,
                                  overwrite=False,
                                  link_to_hfss=True,
                                  export_touchstone=True)
    incident_power = ffdata.incident_power
    ffdata.plot_cut(primary_sweep="Theta", theta=0)
    ffdata.plot_contour(polar=True)
    ffdata.plot_3d(show_geometry=False)
    app.release_desktop(False, False)

If you exported the farfield data previously, you can directly get the farfield data:

.. code:: python

    from ansys.aedt.core.generic.farfield_visualization import FfdSolutionData
    input_file = r"path_to_ffd\pyaedt_antenna_metadata.json"
    ffdata = FfdSolutionData(input_file)
    incident_power = ffdata.incident_power
    ffdata.plot_cut(primary_sweep="Theta", theta=0)
    ffdata.plot_contour(polar=True)
    ffdata.plot_3d(show_geometry=False)
    app.release_desktop(False, False)

The following diagram shows both classes work. You can use them independently or from the ``get_antenna_data`` method.

  .. image:: ../../_static/farfield_visualization_pyaedt.png
    :width: 800
    :alt: Farfield data with PyAEDT


If you have existing farfield data, or you want to export it manually, you can still use FfdSolutionData class.

  .. image:: ../../_static/farfield_visualization_aedt.png
    :width: 800
    :alt: Farfield data with AEDT


Monostatic RCS
~~~~~~~~~~~~~~

PyAEDT offers sophisticated tools for advanced monostatic radar cross section (RCS) post-processing.
There are three complementary classes: ``MonostaticRCSExporter``, ``MonostaticRCSData``, and ``MonostaticRCSPlotter``.

- MonostaticRCSExporter: Enables efficient export and manipulation of RCS data. It allows users to convert simulation results into a standard metadata format for further analysis, or reporting.

- MonostaticRCSData: Focuses on the direct access and processing of RCS solution data. It supports a comprehensive set of postprocessing operations, from visualizing radiation patterns to computing key performance metrics.

- MonostaticRCSPlotter: Focuses on the post-processing of RCS solution data.


.. currentmodule:: ansys.aedt.core.visualization.advanced.rcs_visualization

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   MonostaticRCSData
   MonostaticRCSPlotter


This code shows how you can get the RCS data and perform some post-processing:

.. code:: python

    from ansys.aedt.core import Hfss
    from ansys.aedt.core.visualization.advanced.rcs_visualization import MonostaticRCSPlotter
    app = Hfss()
    rcs_object = app.get_rcs_data()
    rcs_plotter = MonostaticRCSPlotter(rcs_data=rcs_object.rcs_data)
    rcs_plotter.plot_rcs()

If you exported the RCS data previously, you can directly get the RCS data:

.. code:: python

    from ansys.aedt.core.visualization.advanced.rcs_visualization import MonostaticRCSPlotter
    from ansys.aedt.core.visualization.advanced.rcs_visualization import MonostaticRCSData
    input_file = r"path_to_data\pyaedt_rcs_metadata.json"
    rcs_data = MonostaticRCSData(input_file)
    rcs_plotter = MonostaticRCSPlotter(rcs_data)
    rcs_plotter.plot_cut()

The following diagram shows both classes work. You can use them independently or from the ``get_rcs_data`` method.

  .. image:: ../../_static/rcs_visualization_pyaedt.png
    :width: 800
    :alt: RCS data with PyAEDT


Heterogeneous data message
~~~~~~~~~~~~~~~~~~~~~~~~~~

Heterogeneous data message (HDM) is the file exported from SBR+ solver containing rays information.
The following methods allows to read and plot rays information.

.. currentmodule:: ansys.aedt.core.visualization.advanced

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   hdm_plot.HDMPlotter
   sbrplus.hdm_parser.Parser


Miscellaneous
~~~~~~~~~~~~~

PyAEDT has additional advanced post-processing features:

.. currentmodule:: ansys.aedt.core.visualization.advanced.misc

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   convert_nearfield_data
   parse_rdat_file
   nastran_to_stl
   simplify_stl

