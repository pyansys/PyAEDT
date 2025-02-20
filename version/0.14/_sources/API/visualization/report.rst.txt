Report management
=================

AEDT provides extensive flexibility for generating reports.


PyAEDT includes dedicated classes to manipulate all report properties,
offering full control over report customization.

.. note::
   Some functionalities are available only when AEDT is running
   in graphical mode.


.. currentmodule:: ansys.aedt.core.visualization.report

.. autosummary::
   :toctree: _autosummary
   :nosignatures:

   standard.Standard
   standard.Spectral
   field.AntennaParameters
   field.Fields
   field.NearField
   field.FarField
   field.Emission
   eye.EyeDiagram
   eye.AMIConturEyeDiagram
   eye.AMIEyeDiagram
   emi.EMIReceiver


The following code shows how to use report modules in standalone mode.

.. code:: python

    # Create `Mag_E` report in a polyline

    from ansys.aedt.core import Hfss
    from ansys.aedt.core.visualization.report.field import Fields

    app = Hfss(specified_version="2025.1",
               non_graphical=False,
               new_desktop_session=False
               )
    test_points = [["0mm", "0mm", "0mm"], ["100mm", "20mm", "0mm"],
                   ["71mm", "71mm", "0mm"], ["0mm", "100mm", "0mm"]]
    p1 = app.modeler.create_polyline(test_points)
    setup = app.create_setup()

    report = Fields(app=app.post, report_category="Fields",
                    setup_name=setup.name + " : LastAdaptive",
                    expressions="Mag_E")
    report.polyline = p1.name
    report.create()

    app.release_desktop(False, False)


You can use these classes directly from the application object:

.. code:: python

    # Create `Mag_E` report in a polyline

    from ansys.aedt.core import Hfss

    app = Hfss(specified_version="2025.1",
               non_graphical=False,
               new_desktop_session=False
               )
    test_points = [["0mm", "0mm", "0mm"], ["100mm", "20mm", "0mm"],
                   ["71mm", "71mm", "0mm"], ["0mm", "100mm", "0mm"]]
    p1 = app.modeler.create_polyline(test_points)
    setup = app.create_setup()

    report = app.post.reports_by_category.fields("Mag_E", setup.name + " : LastAdaptive", p1.name)
    report.create()

    app.release_desktop(False, False)
