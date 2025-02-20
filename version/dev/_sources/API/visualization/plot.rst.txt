Graphics operations
===================

PyAEDT enables powerful post-processing of AEDT results,
allowing you to visualize graphics objects and plot data with ease.

PyAEDT supports external report capabilities available with installed third-party
packages like `pyvista <https://docs.pyvista.org/>`_, `matplotlib <https://matplotlib.org/>`_,
`pandas <https://pandas.pydata.org/>`_, and `numpy <https://numpy.org/doc/stable/>`_.


There have three main categories:

* **Three-dimensional visualization**
* **Graph visualization**
* **PDF**


Three-dimensional visualization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PyAEDT benefits of `pyvista <https://docs.pyvista.org/>`_ package and allows to generate
models and 3D plots.

.. currentmodule:: ansys.aedt.core.visualization.plot.pyvista

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   ModelPlotter
   FieldClass
   ObjClass


Graph visualization
~~~~~~~~~~~~~~~~~~~

PyAEDT benefits of `matplotlib <https://matplotlib.org/>`_ package and allows to generate 2D plots.


.. currentmodule:: ansys.aedt.core.visualization.plot.matplotlib

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   ReportPlotter
   is_notebook


PDF
~~~

PyAEDT benefits of `fpdf2 <https://py-pdf.github.io/fpdf2/index.html/>`_ package and allows to generate PDF files.

.. currentmodule:: ansys.aedt.core.visualization.plot.pdf

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   AnsysReport.read_template
   AnsysReport.header
   AnsysReport.footer
   AnsysReport.create
   AnsysReport.add_project_info
   AnsysReport.add_section
   AnsysReport.add_chapter
   AnsysReport.add_sub_chapter
   AnsysReport.add_image
   AnsysReport.add_caption
   AnsysReport.add_empty_line
   AnsysReport.add_page_break
   AnsysReport.add_table
   AnsysReport.add_text
   AnsysReport.add_toc
   AnsysReport.save_pdf
   AnsysReport.add_chart
