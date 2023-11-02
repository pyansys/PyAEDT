"""This module contains the `PostProcessor` class.

It contains all advanced postprocessing functionalities that require Python 3.x packages like NumPy and Matplotlib.
"""
from __future__ import absolute_import  # noreorder

import os
import warnings

from pyaedt.generic.general_methods import is_ironpython, open_file, pyaedt_function_handler
from pyaedt.generic.plot import ModelPlotter
from pyaedt.modules.PostProcessor import PostProcessor as Post

if not is_ironpython:
    try:
        import numpy as np
    except ImportError:
        warnings.warn(
            "The NumPy module is required to run some functionalities of PostProcess.\n"
            "Install with \n\npip install numpy\n\nRequires CPython."
        )

    try:
        from IPython.display import Image

        ipython_available = True
    except ImportError:
        ipython_available = False


class PostProcessor(Post):
    """Contains advanced postprocessing functionalities that require Python 3.x packages like NumPy and Matplotlib.

    Parameters
    ----------
    app :
        Inherited parent object.

    Examples
    --------
    Basic usage demonstrated with an HFSS, Maxwell, or any other design:

    >>> from pyaedt import Hfss
    >>> aedtapp = Hfss()
    >>> post = aedtapp.post
    """

    def __init__(self, app):
        Post.__init__(self, app)

    @pyaedt_function_handler()
    def nb_display(self, show_axis=True, show_grid=True, show_ruler=True):
        """Show the Jupyter Notebook display.

          .. note::
              .assign_curvature_extraction Jupyter Notebook is not supported by IronPython.

        Parameters
        ----------
         show_axis : bool, optional
             Whether to show the axes. The default is ``True``.
         show_grid : bool, optional
             Whether to show the grid. The default is ``True``.
         show_ruler : bool, optional
             Whether to show the ruler. The default is ``True``.

        Returns
        -------
        :class:`IPython.core.display.Image`
            Jupyter notebook image.

        """
        if ipython_available:
            file_name = self.export_model_picture(show_axis=show_axis, show_grid=show_grid, show_ruler=show_ruler)
            return Image(file_name, width=500)
        else:
            warnings.warn("The Ipython package is missing and must be installed.")

    @pyaedt_function_handler()
    def get_efields_data(self, setup_sweep_name="", ff_setup="Infinite Sphere1", freq="All"):
        """Compute Etheta and EPhi.

        .. warning::
           This method requires NumPy to be installed on your machine.


        Parameters
        ----------
        setup_sweep_name : str, optional
            Name of the setup for computing the report. The default is ``""``, in
            which case the nominal adaptive is applied.
        ff_setup : str, optional
            Far field setup. The default is ``"Infinite Sphere1"``.
        freq : str, optional
            The default is ``"All"``.

        Returns
        -------
        np.ndarray
            Numpy array containing ``[theta_range, phi_range, Etheta, Ephi]``.
        """
        if not setup_sweep_name:
            setup_sweep_name = self._app.nominal_adaptive
        results_dict = {}
        all_sources = self.post_osolution.GetAllSources()
        # assuming only 1 mode
        all_sources_with_modes = [s + ":1" for s in all_sources]

        for n, source in enumerate(all_sources_with_modes):
            edit_sources_ctxt = [["IncludePortPostProcessing:=", False, "SpecifySystemPower:=", False]]
            for m, each in enumerate(all_sources_with_modes):
                if n == m:  # set only 1 source to 1W, all the rest to 0
                    mag = 1
                else:
                    mag = 0
                phase = 0
                edit_sources_ctxt.append(
                    ["Name:=", "{}".format(each), "Magnitude:=", "{}W".format(mag), "Phase:=", "{}deg".format(phase)]
                )
            self.post_osolution.EditSources(edit_sources_ctxt)

            ctxt = ["Context:=", ff_setup]

            sweeps = ["Theta:=", ["All"], "Phi:=", ["All"], "Freq:=", [freq]]

            trace_name = "rETheta"
            solnData = self.get_far_field_data(
                setup_sweep_name=setup_sweep_name, domain=ff_setup, expression=trace_name
            )

            data = solnData.nominal_variation

            theta_vals = np.degrees(np.array(data.GetSweepValues("Theta")))
            phi_vals = np.degrees(np.array(data.GetSweepValues("Phi")))
            # phi is outer loop
            theta_unique = np.unique(theta_vals)
            phi_unique = np.unique(phi_vals)
            theta_range = np.linspace(np.min(theta_vals), np.max(theta_vals), np.size(theta_unique))
            phi_range = np.linspace(np.min(phi_vals), np.max(phi_vals), np.size(phi_unique))
            real_theta = np.array(data.GetRealDataValues(trace_name))
            imag_theta = np.array(data.GetImagDataValues(trace_name))

            trace_name = "rEPhi"
            solnData = self.get_far_field_data(
                setup_sweep_name=setup_sweep_name, domain=ff_setup, expression=trace_name
            )
            data = solnData.nominal_variation

            real_phi = np.array(data.GetRealDataValues(trace_name))
            imag_phi = np.array(data.GetImagDataValues(trace_name))

            Etheta = np.vectorize(complex)(real_theta, imag_theta)
            Ephi = np.vectorize(complex)(real_phi, imag_phi)
            source_name_without_mode = source.replace(":1", "")
            results_dict[source_name_without_mode] = [theta_range, phi_range, Etheta, Ephi]
        return results_dict

    @pyaedt_function_handler()
    def get_model_plotter_geometries(
        self,
        objects=None,
        plot_as_separate_objects=True,
        plot_air_objects=False,
        force_opacity_value=None,
        array_coordinates=None,
        generate_mesh=True,
        get_objects_from_aedt=True,
    ):
        """Initialize the Model Plotter object with actual modeler objects and return it.

        Parameters
        ----------
        objects : list, optional
            Optional list of objects to plot. If `None` all objects will be exported.
        plot_as_separate_objects : bool, optional
            Plot each object separately. It may require more time to export from AEDT.
        plot_air_objects : bool, optional
            Plot also air and vacuum objects.
        force_opacity_value : float, optional
            Opacity value between 0 and 1 to be applied to all model.
            If `None` aedt opacity will be applied to each object.
        array_coordinates : list of list
            List of array element centers. The modeler objects will be duplicated and translated.
            List of [[x1,y1,z1], [x2,y2,z2]...].
        generate_mesh : bool, optional
            Whether to generate the mesh after importing objects. The default is ``True``.
        get_objects_from_aedt : bool, optional
            Whether to export objects from AEDT and initialize them. The default is ``True``.

        Returns
        -------
        :class:`pyaedt.generic.plot.ModelPlotter`
            Model Object.
        """
        assert self._app._aedt_version >= "2021.2", self.logger.error("Object is supported from AEDT 2021 R2.")

        files = []
        if get_objects_from_aedt and self._app.solution_type not in ["HFSS3DLayout", "HFSS 3D Layout Design"]:
            files = self.export_model_obj(
                obj_list=objects,
                export_as_single_objects=plot_as_separate_objects,
                air_objects=plot_air_objects,
            )

        model = ModelPlotter()
        model.off_screen = True
        units = self.modeler.model_units
        for file in files:
            if force_opacity_value:
                model.add_object(file[0], file[1], force_opacity_value, units)
            else:
                model.add_object(file[0], file[1], file[2], units)
        model.array_coordinates = array_coordinates
        if generate_mesh:
            model.generate_geometry_mesh()
        return model

    @pyaedt_function_handler()
    def plot_model_obj(
        self,
        objects=None,
        show=True,
        export_path=None,
        plot_as_separate_objects=True,
        plot_air_objects=False,
        force_opacity_value=None,
        clean_files=False,
        array_coordinates=None,
        view="isometric",
        show_legend=True,
        dark_mode=False,
        show_bounding=False,
        show_grid=False,
    ):
        """Plot the model or a substet of objects.

        Parameters
        ----------
        objects : list, optional
            Optional list of objects to plot. If `None` all objects will be exported.
        show : bool, optional
            Show the plot after generation or simply return the
            generated Class for more customization before plot.
        export_path : str, optional
            If available, an image is saved to file. If `None` no image will be saved.
        plot_as_separate_objects : bool, optional
            Plot each object separately. It may require more time to export from AEDT.
        plot_air_objects : bool, optional
            Plot also air and vacuum objects.
        force_opacity_value : float, optional
            Opacity value between 0 and 1 to be applied to all model.
            If `None` aedt opacity will be applied to each object.
        clean_files : bool, optional
            Clean created files after plot. Cache is mainteined into the model object returned.
        array_coordinates : list of list
            List of array element centers. The modeler objects will be duplicated and translated.
            List of [[x1,y1,z1], [x2,y2,z2]...].
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, ``"yz"``.
            The default is ``"isometric"``.
        show_legend : bool, optional
            Whether to display the legend or not. The default is ``True``.
        dark_mode : bool, optional
            Whether to display the model in dark mode or not. The default is ``False``.
        show_grid : bool, optional
            Whether to display the axes grid or not. The default is ``False``.
        show_bounding : bool, optional
            Whether to display the axes bounding box or not. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.generic.plot.ModelPlotter`
            Model Object.
        """
        model = self.get_model_plotter_geometries(
            objects=objects,
            plot_as_separate_objects=plot_as_separate_objects,
            plot_air_objects=plot_air_objects,
            force_opacity_value=force_opacity_value,
            array_coordinates=array_coordinates,
            generate_mesh=False,
        )

        model.show_legend = show_legend
        model.off_screen = not show
        if dark_mode:
            model.background_color = [40, 40, 40]
        model.bounding_box = show_bounding
        model.show_grid = show_grid
        if view != "isometric" and view in ["xy", "xz", "yz"]:
            model.camera_position = view
        elif view != "isometric":
            self.logger.warning("Wrong view setup. It has to be one of xy, xz, yz, isometric.")
        if export_path:
            model.plot(export_path)
        elif show:
            model.plot()
        if clean_files:
            model.clean_cache_and_files(clean_cache=False)
        return model

    @pyaedt_function_handler()
    def plot_field_from_fieldplot(
        self,
        plotname,
        project_path="",
        meshplot=False,
        imageformat="jpg",
        view="isometric",
        plot_label="Temperature",
        plot_folder=None,
        show=True,
        scale_min=None,
        scale_max=None,
        plot_cad_objs=True,
        log_scale=True,
        dark_mode=False,
        show_grid=False,
        show_bounding=False,
        show_legend=True,
        plot_as_separate_objects=True,
    ):
        """Export a field plot to an image file (JPG or PNG) using Python PyVista.

        .. note::
           The PyVista module rebuilds the mesh and the overlap fields on the mesh.

        Parameters
        ----------
        plotname : str
            Name of the field plot to export.
        project_path : str, optional
            Path for saving the image file. The default is ``""``.
        meshplot : bool, optional
            Whether to create and plot the mesh over the fields. The
            default is ``False``.
        imageformat : str, optional
            Format of the image file. Options are ``"jpg"``,
            ``"png"``, ``"svg"``, and ``"webp"``. The default is
            ``"jpg"``.
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, ``"yz"``.
        plot_label : str, optional
            Type of the plot. The default is ``"Temperature"``.
        plot_folder : str, optional
            Plot folder to update before exporting the field.
            The default is ``None``, in which case all plot
            folders are updated.
        show : bool, optional
            Export Image without plotting on UI.
        scale_min : float, optional
            Fix the Scale Minimum value.
        scale_max : float, optional
            Fix the Scale Maximum value.
        plot_cad_objs : bool, optional
            Whether to include objects in the plot. The default is ``True``.
        log_scale : bool, optional
            Whether to plot fields in log scale. The default is ``True``.
        dark_mode : bool, optional
            Whether to display the model in dark mode or not. The default is ``False``.
        show_grid : bool, optional
            Whether to display the axes grid or not. The default is ``False``.
        show_bounding : bool, optional
            Whether to display the axes bounding box or not. The default is ``False``.
        show_legend : bool, optional
            Whether to display the legend or not. The default is ``True``.
        plot_as_separate_objects : bool, optional
            Plot each object separately. It may require more time to export from AEDT.

        Returns
        -------
        :class:`pyaedt.generic.plot.ModelPlotter`
            Model Object.
        """
        is_pcb = False
        if self._app.solution_type in ["HFSS3DLayout", "HFSS 3D Layout Design"]:
            is_pcb = True
        if not plot_folder:
            self.ofieldsreporter.UpdateAllFieldsPlots()
        else:
            self.ofieldsreporter.UpdateQuantityFieldsPlots(plot_folder)

        file_to_add = self.export_field_plot(plotname, self._app.working_directory, file_format="case")
        model = self.get_model_plotter_geometries(
            generate_mesh=False,
            get_objects_from_aedt=plot_cad_objs,
            plot_as_separate_objects=plot_as_separate_objects,
        )
        model.show_legend = show_legend
        model.off_screen = not show
        if dark_mode:
            model.background_color = [40, 40, 40]
        model.bounding_box = show_bounding
        model.show_grid = show_grid
        if file_to_add:
            model.add_field_from_file(
                file_to_add,
                coordinate_units=self.modeler.model_units,
                show_edges=meshplot,
                log_scale=log_scale,
            )
            if plot_label:
                model.fields[0].label = plot_label

        if view != "isometric" and view in ["xy", "xz", "yz"]:
            model.camera_position = view
        elif view != "isometric":
            self.logger.warning("Wrong view setup. It has to be one of xy, xz, yz, isometric.")
        if is_pcb:
            model.z_scale = 5

        if scale_min and scale_max:
            model.range_min = scale_min
            model.range_max = scale_max
        if project_path:
            model.plot(os.path.join(project_path, plotname + "." + imageformat))
        elif show:
            model.plot()
        return model

    @pyaedt_function_handler()
    def plot_field(
        self,
        quantity,
        object_list,
        plot_type="Surface",
        setup_name=None,
        intrinsics=None,
        mesh_on_fields=False,
        view="isometric",
        plot_label=None,
        show=True,
        scale_min=None,
        scale_max=None,
        plot_cad_objs=True,
        log_scale=False,
        export_path="",
        imageformat="jpg",
        keep_plot_after_generation=False,
        dark_mode=False,
        show_bounding=False,
        show_grid=False,
        show_legend=True,
        filter_objects=[],
        plot_as_separate_objects=True,
    ):
        """Create a field plot  using Python PyVista and export to an image file (JPG or PNG).

        .. note::
           The PyVista module rebuilds the mesh and the overlap fields on the mesh.

        Parameters
        ----------
        quantity : str
            Quantity to plot (e.g. ``"Mag_E"``).
        object_list : str, list
            Objects or faces to which apply the Field Plot.
        plot_type  : str, optional
            Plot type. Options are ``"Surface"``, ``"Volume"``, ``"CutPlane"``.
        setup_name : str, optional
            Setup and sweep name on which create the field plot. Default is None for nominal setup usage.
        intrinsics : dict, optional.
            Intrinsic dictionary that is needed for the export.
            The default is ``None`` which try to retrieve intrinsics from setup.
        mesh_on_fields : bool, optional
            Whether to create and plot the mesh over the fields. The
            default is ``False``.
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, ``"yz"``.
        plot_label : str, optional
            Type of the plot. The default is ``"Temperature"``.
        show : bool, optional
            Export Image without plotting on UI.
        scale_min : float, optional
            Fix the Scale Minimum value.
        scale_max : float, optional
            Fix the Scale Maximum value.
        plot_cad_objs : bool, optional
            Whether to include objects in the plot. The default is ``True``.
        log_scale : bool, optional
            Whether to plot fields in log scale. The default is ``False``.
        export_path : str, optional
            Image export path. Default is ``None`` to not export the image.
        imageformat : str, optional
            Format of the image file. Options are ``"jpg"``,
            ``"png"``, ``"svg"``, and ``"webp"``. The default is
            ``"jpg"``.
        keep_plot_after_generation : bool, optional
            Either to keep the Field Plot in AEDT after the generation is completed. Default is ``False``.
        dark_mode : bool, optional
            Whether to display the model in dark mode or not. The default is ``False``.
        show_grid : bool, optional
            Whether to display the axes grid or not. The default is ``False``.
        show_bounding : bool, optional
            Whether to display the axes bounding box or not. The default is ``False``.
        show_legend : bool, optional
            Whether to display the legend or not. The default is ``True``.
        filter_objects : list, optional
            Objects list for filtering the ``CutPlane`` plots.
        plot_as_separate_objects : bool, optional
            Plot each object separately. It may require more time to export from AEDT.

        Returns
        -------
        :class:`pyaedt.generic.plot.ModelPlotter`
            Model Object.
        """
        if os.getenv("PYAEDT_DOC_GENERATION", "False").lower() in ("true", "1", "t"):  # pragma: no cover
            show = False
        if not setup_name:
            setup_name = self._app.existing_analysis_sweeps[0]
        if not intrinsics:
            for i in self._app.setups:
                if i.name == setup_name.split(" : ")[0]:
                    intrinsics = i.default_intrinsics

        # file_to_add = []
        if plot_type == "Surface":
            plotf = self.create_fieldplot_surface(object_list, quantity, setup_name, intrinsics)
        elif plot_type == "Volume":
            plotf = self.create_fieldplot_volume(object_list, quantity, setup_name, intrinsics)
        else:
            plotf = self.create_fieldplot_cutplane(
                object_list, quantity, setup_name, intrinsics, filter_objects=filter_objects
            )
        # if plotf:
        #     file_to_add = self.export_field_plot(plotf.name, self._app.working_directory, plotf.name)

        model = self.plot_field_from_fieldplot(
            plotf.name,
            export_path,
            mesh_on_fields,
            imageformat,
            view,
            plot_label if plot_label else quantity,
            None,
            show,
            scale_min,
            scale_max,
            plot_cad_objs,
            log_scale,
            dark_mode=dark_mode,
            show_grid=show_grid,
            show_bounding=show_bounding,
            show_legend=show_legend,
            plot_as_separate_objects=plot_as_separate_objects,
        )
        if not keep_plot_after_generation:
            plotf.delete()
        return model

    @pyaedt_function_handler()
    def plot_animated_field(
        self,
        quantity,
        object_list,
        plot_type="Surface",
        setup_name=None,
        intrinsics=None,
        variation_variable="Phi",
        variation_list=["0deg"],
        view="isometric",
        plot_label=None,
        show=True,
        scale_min=None,
        scale_max=None,
        plot_cad_objs=True,
        log_scale=True,
        zoom=None,
        export_gif=False,
        export_path="",
        force_opacity_value=0.1,
        dark_mode=False,
        show_grid=False,
        show_bounding=False,
        show_legend=True,
        filter_objects=[],
    ):
        """Create an animated field plot using Python PyVista and export to a gif file.

        .. note::
           The PyVista module rebuilds the mesh and the overlap fields on the mesh.

        Parameters
        ----------
        quantity : str
            Quantity to plot (e.g. ``"Mag_E"``).
        object_list : list, str
            List of objects or faces to which apply the Field Plot.
        plot_type  : str, optional
            Plot type. Options are ``"Surface"``, ``"Volume"``, ``"CutPlane"``.
        setup_name : str, optional
            Setup and sweep name on which create the field plot. Default is None for nominal setup usage.
        intrinsics : dict, optional.
            Intrinsic dictionary that is needed for the export.
            The default is ``None`` which try to retrieve intrinsics from setup.
        variation_variable : str, optional
            Variable to vary. The default is ``"Phi"``.
        variation_list : list, optional
            List of variation values with units. The default is
            ``["0deg"]``.
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, ``"yz"``.
        show : bool, optional
            Export Image without plotting on UI.
        scale_min : float, optional
            Fix the Scale Minimum value.
        scale_max : float, optional
            Fix the Scale Maximum value.
        plot_cad_objs : bool, optional
            Whether to include objects in the plot. The default is ``True``.
        log_scale : bool, optional
            Whether to plot fields in log scale. The default is ``True``.
        zoom : float, optional
            Zoom factor.
        export_gif : bool, optional
             Whether to export an animated gif or not. The default is ``False``.
        export_path : str, optional
            Image export path. Default is ``None`` to not ``working_directory`` will be used to save the image.
        force_opacity_value : float, optional
            Opacity value between 0 and 1 to be applied to all model.
            If `None` aedt opacity will be applied to each object.
        dark_mode : bool, optional
            Whether to display the model in dark mode or not. The default is ``False``.
        show_grid : bool, optional
            Whether to display the axes grid or not. The default is ``False``.
        show_bounding : bool, optional
            Whether to display the axes bounding box or not. The default is ``False``.
        show_legend : bool, optional
            Whether to display the legend or not. The default is ``True``.
        filter_objects : list, optional
            Objects list for filtering the ``CutPlane`` plots.

        Returns
        -------
        :class:`pyaedt.generic.plot.ModelPlotter`
            Model Object.
        """
        if os.getenv("PYAEDT_DOC_GENERATION", "False").lower() in ("true", "1", "t"):  # pragma: no cover
            show = False
        if intrinsics is None:
            intrinsics = {}
        if not export_path:
            export_path = self._app.working_directory

        v = 0
        fields_to_add = []
        is_intrinsics = True
        if variation_variable in self._app.variable_manager.independent_variables:
            is_intrinsics = False
        for el in variation_list:
            if is_intrinsics:
                intrinsics[variation_variable] = el
            else:
                self._app[variation_variable] = el
            if plot_type == "Surface":
                plotf = self.create_fieldplot_surface(object_list, quantity, setup_name, intrinsics)
            elif plot_type == "Volume":
                plotf = self.create_fieldplot_volume(object_list, quantity, setup_name, intrinsics)
            else:
                plotf = self.create_fieldplot_cutplane(
                    object_list, quantity, setup_name, intrinsics, filter_objects=filter_objects
                )
            if plotf:
                file_to_add = self.export_field_plot(plotf.name, export_path, plotf.name + str(v), file_format="case")
                if file_to_add:
                    fields_to_add.append(file_to_add)
                plotf.delete()
            v += 1
        model = self.get_model_plotter_geometries(
            generate_mesh=False, get_objects_from_aedt=plot_cad_objs, force_opacity_value=force_opacity_value
        )
        model.off_screen = not show
        if dark_mode:
            model.background_color = [40, 40, 40]
        model.bounding_box = show_bounding
        model.show_grid = show_grid
        model.show_legend = show_legend
        if fields_to_add:
            model.add_frames_from_file(fields_to_add, log_scale=log_scale)
        if export_gif:
            model.gif_file = os.path.join(self._app.working_directory, self._app.project_name + ".gif")
        if view != "isometric" and view in ["xy", "xz", "yz"]:
            model.camera_position = view
        elif view != "isometric":
            self.logger.warning("Wrong view setup. It has to be one of xy, xz, yz, isometric.")

        if scale_min and scale_max:
            model.range_min = scale_min
            model.range_max = scale_max
        if zoom:
            model.zoom = zoom
        if show or export_gif:
            model.animate()
        return model

    @pyaedt_function_handler()
    def animate_fields_from_aedtplt(
        self,
        plotname,
        plot_folder=None,
        meshplot=False,
        variation_variable="Phase",
        variation_list=["0deg"],
        project_path="",
        export_gif=False,
        show=True,
        dark_mode=False,
        show_bounding=False,
        show_grid=False,
    ):
        """Generate a field plot to an image file (JPG or PNG) using PyVista.

        .. note::
           The PyVista module rebuilds the mesh and the overlap fields on the mesh.

        Parameters
        ----------
        plotname : str
            Name of the plot or the name of the object.
        plot_folder : str, optional
            Name of the folder in which the plot resides. The default
            is ``None``.
        variation_variable : str, optional
            Variable to vary. The default is ``"Phase"``.
        variation_list : list, optional
            List of variation values with units. The default is
            ``["0deg"]``.
        project_path : str, optional
            Path for the export. The default is ``""`` which export file in working_directory.
        meshplot : bool, optional
             The default is ``False``. Valid from Version 2021.2.
        export_gif : bool, optional
             The default is ``False``.
                show=False,
        show : bool, optional
             Generate the animation without showing an interactive plot.  The default is ``True``.
        dark_mode : bool, optional
            Whether to display the model in dark mode or not. The default is ``False``.
        show_grid : bool, optional
            Whether to display the axes grid or not. The default is ``False``.
        show_bounding : bool, optional
            Whether to display the axes bounding box or not. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.generic.plot.ModelPlotter`
            Model Object.
        """
        if not plot_folder:
            self.ofieldsreporter.UpdateAllFieldsPlots()
        else:
            self.ofieldsreporter.UpdateQuantityFieldsPlots(plot_folder)

        fields_to_add = []
        if not project_path:
            project_path = self._app.working_directory
        for el in variation_list:
            if plotname in self.field_plots and variation_variable in self.field_plots[plotname].intrinsincList:
                self.field_plots[plotname].intrinsincList[variation_variable] = el
                self.field_plots[plotname].update()
            else:
                self._app._odesign.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            "NAME:FieldsPostProcessorTab",
                            ["NAME:PropServers", "FieldsReporter:" + plotname],
                            ["NAME:ChangedProps", ["NAME:" + variation_variable, "Value:=", el]],
                        ],
                    ]
                )
            fields_to_add.append(
                self.export_field_plot(
                    plotname, project_path, plotname + variation_variable + str(el), file_format="case"
                )
            )

        model = self.get_model_plotter_geometries(generate_mesh=False)
        model.off_screen = not show
        if dark_mode:
            model.background_color = [40, 40, 40]
        model.bounding_box = show_bounding
        model.show_grid = show_grid
        if fields_to_add:
            model.add_frames_from_file(fields_to_add)
        if export_gif:
            model.gif_file = os.path.join(self._app.working_directory, self._app.project_name + ".gif")

        if show or export_gif:
            model.animate()
        return model

    @pyaedt_function_handler()
    def animate_fields_from_aedtplt_2(
        self,
        quantityname,
        object_list,
        plottype,
        meshplot=False,
        setup_name=None,
        intrinsic_dict={},
        variation_variable="Phi",
        variation_list=["0deg"],
        project_path="",
        export_gif=False,
        show=True,
        zoom=None,
        log_scale=False,
        dark_mode=False,
        show_grid=False,
        show_bounding=False,
    ):
        """Generate a field plot to an animated gif file using PyVista.

        .. deprecated:: 0.6.83
            No need to use primitives anymore. You can instantiate primitives methods directly from modeler instead.

         .. note::
            The PyVista module rebuilds the mesh and the overlap fields on the mesh.

        This method creates the plot and exports it.
        It is an alternative to the method :func:`animate_fields_from_aedtplt`,
        which uses an existing plot.

        Parameters
        ----------
        quantityname : str
            Name of the plot or the name of the object.
        object_list : list, optional
            Name of the ``folderplot`` folder.
        plottype : str
            Type of the plot. Options are ``"Surface"``, ``"Volume"``, and
            ``"CutPlane"``.
        meshplot : bool, optional
            The default is ``False``.
        setup_name : str, optional
            Name of the setup (sweep) to use for the export. The default is
            ``None``.
        intrinsic_dict : dict, optional
            Intrinsic dictionary that is needed for the export.
            The default is ``{}``.
        variation_variable : str, optional
            Variable to vary. The default is ``"Phi"``.
        variation_list : list, option
            List of variation values with units. The default is
            ``["0deg"]``.
        project_path : str, optional
            Path for the export. The default is ``""`` which export file in working_directory.
        export_gif : bool, optional
            Whether to export to a GIF file. The default is ``False``,
            in which case the plot is exported to a JPG file.
        show : bool, optional
            Generate the animation without showing an interactive plot.  The default is ``True``.
        zoom : float, optional
            Zoom factor.
        log_scale : bool, optional
            Whether to plot fields in log scale. The default is ``True``.

        Returns
        -------
        :class:`pyaedt.generic.plot.ModelPlotter`
            Model Object.
        """
        warnings.warn(
            "`animate_fields_from_aedtplt_2` is deprecated. Use `plot_animated_field` property instead.",
            DeprecationWarning,
        )

        return self.plot_animated_field(
            quantity=quantityname,
            object_list=object_list,
            plot_type=plottype,
            setup_name=setup_name,
            intrinsics=intrinsic_dict,
            variation_variable=variation_variable,
            variation_list=variation_list,
            export_path=project_path,
            log_scale=log_scale,
            show=show,
            export_gif=export_gif,
            zoom=zoom,
            show_bounding=show_bounding,
            show_grid=show_grid,
            dark_mode=dark_mode,
        )

    @pyaedt_function_handler()
    def create_3d_plot(
        self, solution_data, nominal_sweep=None, nominal_value=None, primary_sweep="Theta", secondary_sweep="Phi"
    ):
        """Create a 3D plot using Matplotlib.

        Parameters
        ----------
        solution_data : :class:`pyaedt.modules.solutions.SolutionData`
            Input data for the solution.
        nominal_sweep : str, optional
            Name of the nominal sweep. The default is ``None``.
        nominal_value : str, optional
            Value for the nominal sweep. The default is ``None``.
        primary_sweep : str, optional
            Primary sweep. The default is ``"Theta"``.
        secondary_sweep : str, optional
            Secondary sweep. The default is ``"Phi"``.

        Returns
        -------
         bool
             ``True`` when successful, ``False`` when failed.
        """
        if nominal_value:
            solution_data.intrinsics[nominal_sweep] = nominal_value
        if nominal_value:
            solution_data.primary_sweep = primary_sweep
        return solution_data.plot_3d(x_axis=primary_sweep, y_axis=secondary_sweep)

    @pyaedt_function_handler()
    def plot_scene(
        self,
        frames_list,
        output_gif_path,
        norm_index=0,
        dy_rng=0,
        fps=30,
        show=True,
        view="yz",
        zoom=2.0,
        convert_fields_in_db=False,
        log_multiplier=10.0,
    ):
        """Plot the current model 3D scene with overlapping animation coming from a file list and save the gif.

        Parameters
        ----------
        frames_list : list or str
            File list containing animation frames to plot in csv format or
            path to a txt index file containing full path to csv files.
        output_gif_path : str
            Full path to output gif file.
        norm_index : int, optional
            Pick the frame to use to normalize your images.
            Data is already saved as dB : 100 for usual traffic scenes.
        dy_rng : int, optional
            Specify how many dB below you would like to specify the range_min.
            Tweak this a couple of times with small number of frames.
        fps : int, optional
            Frames per Second.
        show : bool, optional
            Either if show or only export gif.
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, and ``"yz"``.
           The default is ``"isometric"``.
        zoom : float, optional
            Default zoom. Default Value is `2`.
        convert_fields_in_db : bool, optional
            Either if convert the fields before plotting in dB. Default Value is `False`.
        log_multiplier : float, optional
            Field multiplier if field in dB. Default Value is `10.0`.

        Returns
        -------

        """
        if isinstance(frames_list, str) and os.path.exists(frames_list):
            with open_file(frames_list, "r") as f:
                lines = f.read()
                temp_list = lines.splitlines()
            frames_paths_list = [i for i in temp_list]
        elif isinstance(frames_list, str):
            self.logger.error("Path doesn't exists")
            return False
        else:
            frames_paths_list = frames_list
        scene = self.get_model_plotter_geometries(generate_mesh=False)

        norm_data = np.loadtxt(frames_paths_list[norm_index], skiprows=1, delimiter=",")
        norm_val = norm_data[:, -1]
        v_max = np.max(norm_val)
        v_min = v_max - dy_rng
        scene.add_frames_from_file(frames_paths_list, log_scale=False, color_map="jet", header_lines=1, opacity=0.8)

        # Specifying the attributes of the scene through the ModelPlotter object
        scene.off_screen = not show
        if view != "isometric" and view in ["xy", "xz", "yz"]:
            scene.camera_position = view
        scene.range_min = v_min
        scene.range_max = v_max
        scene.show_grid = False
        scene.windows_size = [1920, 1080]
        scene.show_legend = False
        scene.show_boundingbox = False
        scene.legend = False
        scene.frame_per_seconds = fps
        scene.zoom = zoom
        scene.bounding_box = False
        scene.color_bar = False
        scene.gif_file = output_gif_path  # This gif may be a bit slower so we can speed it up a bit
        scene.convert_fields_in_db = convert_fields_in_db
        scene.log_multiplier = log_multiplier
        scene.animate()
