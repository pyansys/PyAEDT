from __future__ import absolute_import  # noreorder

import math
import os
import time
import warnings

from pyaedt.edb_core.edb_data.nets_data import EDBNetsData
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.generic.constants import CSS4_COLORS
from pyaedt.generic.general_methods import generate_unique_name, is_ironpython, pyaedt_function_handler
from pyaedt.modeler.geometry_operators import GeometryOperators


class EdbNets(object):
    """Manages EDB methods for nets management accessible from `Edb.nets` property.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edbapp = Edb("myaedbfolder", edbversion="2021.2")
    >>> edb_nets = edbapp.nets
    """

    @pyaedt_function_handler()
    def __getitem__(self, name):
        """Get  a net from the Edb project.

        Parameters
        ----------
        name : str, int

        Returns
        -------
        :class:` :class:`pyaedt.edb_core.edb_data.nets_data.EDBNetsData`

        """
        if name in self.nets:
            return self.nets[name]
        self._pedb.logger.error("Component or definition not found.")
        return

    def __init__(self, p_edb):
        self._pedb = p_edb
        self._nets_by_comp_dict = {}
        self._comps_by_nets_dict = {}

    @property
    def _edb(self):
        """ """
        return self._pedb.edb_api

    @property
    def _active_layout(self):
        """ """
        return self._pedb.active_layout

    @property
    def _layout(self):
        """ """
        return self._pedb.layout

    @property
    def _cell(self):
        """ """
        return self._pedb.cell

    @property
    def db(self):
        """Db object."""
        return self._pedb.active_db

    @property
    def _logger(self):
        """Edb logger."""
        return self._pedb.logger

    @property
    def nets(self):
        """Nets.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.nets_data.EDBNetsData`]
            Dictionary of nets.
        """
        temp = {}
        for net in self._layout.nets:
            temp[net.name] = EDBNetsData(net.api_object, self._pedb)
        return temp

    @property
    def netlist(self):
        """Return the cell netlist.

        Returns
        -------
        list
            Net names.
        """
        return list(self.nets.keys())

    @property
    def signal_nets(self):
        """Signal nets.

        .. deprecated:: 0.6.62
           Use :func:`signal` instead.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.EDBNetsData`]
            Dictionary of signal nets.
        """
        warnings.warn("Use :func:`signal` instead.", DeprecationWarning)
        return self.signal

    @property
    def power_nets(self):
        """Power nets.

        .. deprecated:: 0.6.62
           Use :func:`power` instead.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.EDBNetsData`]
            Dictionary of power nets.
        """
        warnings.warn("Use :func:`power` instead.", DeprecationWarning)
        return self.power

    @property
    def signal(self):
        """Signal nets.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.EDBNetsData`]
            Dictionary of signal nets.
        """
        nets = {}
        for net, value in self.nets.items():
            if not value.IsPowerGround():
                nets[net] = value
        return nets

    @property
    def power(self):
        """Power nets.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.EDBNetsData`]
            Dictionary of power nets.
        """
        nets = {}
        for net, value in self.nets.items():
            if value.IsPowerGround():
                nets[net] = value
        return nets

    @pyaedt_function_handler()
    def eligible_power_nets(self, threshold=0.3):
        """Return a list of nets calculated by area to be eligible for PWR/Ground net classification.
            It uses the same algorithm implemented in SIwave.

        Parameters
        ----------
        threshold : float, optional
           Area ratio used by the ``get_power_ground_nets`` method.

        Returns
        -------
        list of  :class:`pyaedt.edb_core.edb_data.EDBNetsData`
        """
        pwr_gnd_nets = []
        for net in self._layout.nets[:]:
            total_plane_area = 0.0
            total_trace_area = 0.0
            for primitive in net.Primitives:
                if primitive.GetPrimitiveType() == self._edb.cell.primitive.PrimitiveType.Bondwire:
                    continue
                if primitive.GetPrimitiveType() != self._edb.cell.primitive.PrimitiveType.Path:
                    total_plane_area += float(primitive.GetPolygonData().Area())
                else:
                    total_trace_area += float(primitive.GetPolygonData().Area())
            if total_plane_area == 0.0:
                continue
            if total_trace_area == 0.0:
                pwr_gnd_nets.append(EDBNetsData(net.api_object, self._pedb))
                continue
            if total_plane_area > 0.0 and total_trace_area > 0.0:
                if total_plane_area / (total_plane_area + total_trace_area) > threshold:
                    pwr_gnd_nets.append(EDBNetsData(net.api_object, self._pedb))
        return pwr_gnd_nets

    @property
    def nets_by_components(self):
        # type: () -> dict
        """Get all nets for each component instance."""
        for comp, i in self._pedb.components.instances.items():
            self._nets_by_comp_dict[comp] = i.nets
        return self._nets_by_comp_dict

    @property
    def components_by_nets(self):
        # type: () -> dict
        """Get all component instances grouped by nets."""
        for comp, i in self._pedb.components.instances.items():
            for n in i.nets:
                if n in self._comps_by_nets_dict:
                    self._comps_by_nets_dict[n].append(comp)
                else:
                    self._comps_by_nets_dict[n] = [comp]
        return self._comps_by_nets_dict

    @pyaedt_function_handler()
    def generate_extended_nets(
        self,
        resistor_below=10,
        inductor_below=1,
        capacitor_above=1,
        exception_list=None,
        include_signal=True,
        include_power=True,
    ):
        # type: (int | float, int | float, int |float, list, bool, bool) -> list
        """Get extended net and associated components.

        Parameters
        ----------
        resistor_below : int, float, optional
            Threshold of resistor value. Search extended net across resistors which has value lower than the threshold.
        inductor_below : int, float, optional
            Threshold of inductor value. Search extended net across inductances which has value lower than the
            threshold.
        capacitor_above : int, float, optional
            Threshold of capacitor value. Search extended net across capacitors which has value higher than the
            threshold.
        exception_list : list, optional
            List of components to bypass when performing threshold checks. Components
            in the list are considered as serial components. The default is ``None``.
        include_signal : str, optional
            Whether to generate extended signal nets. The default is ``True``.
        include_power : str, optional
            Whether to generate extended power nets. The default is ``True``.

        Returns
        -------
        list
            List of all extended nets.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> app = Edb()
        >>> app.nets.get_extended_nets()
        """
        if exception_list is None:
            exception_list = []
        _extended_nets = []
        _nets = self.nets
        all_nets = list(_nets.keys())[:]
        net_dicts = self._comps_by_nets_dict if self._comps_by_nets_dict else self.components_by_nets
        comp_dict = self._nets_by_comp_dict if self._nets_by_comp_dict else self.nets_by_components

        def get_net_list(net_name, _net_list):
            comps = []
            if net_name in net_dicts:
                comps = net_dicts[net_name]

            for vals in comps:
                refdes = vals
                cmp = self._pedb.components.instances[refdes]
                is_enabled = cmp.is_enabled
                if not is_enabled:
                    continue
                val_type = cmp.type
                if val_type not in ["Inductor", "Resistor", "Capacitor"]:
                    continue

                val_value = cmp.rlc_values
                if refdes in exception_list:
                    pass
                elif val_type == "Inductor" and val_value[1] < inductor_below:
                    pass
                elif val_type == "Resistor" and val_value[0] < resistor_below:
                    pass
                elif val_type == "Capacitor" and val_value[2] > capacitor_above:
                    pass
                else:
                    continue

                for net in comp_dict[refdes]:
                    if net not in _net_list:
                        _net_list.append(net)
                        get_net_list(net, _net_list)

        while len(all_nets) > 0:
            new_ext = [all_nets[0]]
            get_net_list(new_ext[0], new_ext)
            all_nets = [i for i in all_nets if i not in new_ext]
            _extended_nets.append(new_ext)

            if len(new_ext) > 1:
                i = new_ext[0]
                for i in new_ext:
                    if not i.lower().startswith("unnamed"):
                        break

                is_power = False
                for i in new_ext:
                    is_power = is_power or _nets[i].is_power_ground

                if is_power:
                    if include_power:
                        self._pedb.extended_nets.create(i, new_ext)
                    else:  # pragma: no cover
                        pass
                else:
                    if include_signal:
                        self._pedb.extended_nets.create(i, new_ext)
                    else:  # pragma: no cover
                        pass

        return _extended_nets

    @staticmethod
    def _eval_arc_points(p1, p2, h, n=6, tol=1e-12):
        """Get the points of the arc.

        Parameters
        ----------
        p1 : list
            Arc starting point.
        p2 : list
            Arc ending point.
        h : float
            Arc height.
        n : int
            Number of points to generate along the arc.
        tol : float
            Geometric tolerance.

        Returns
        -------
        list
            points generated along the arc.
        """
        # fmt: off
        if abs(h) < tol:
            return [], []
        elif h > 0:
            reverse = False
            x1 = p1[0]
            y1 = p1[1]
            x2 = p2[0]
            y2 = p2[1]
        else:
            reverse = True
            x1 = p2[0]
            y1 = p2[1]
            x2 = p1[0]
            y2 = p1[1]
            h *= -1
        xa = (x2 - x1) / 2
        ya = (y2 - y1) / 2
        xo = x1 + xa
        yo = y1 + ya
        a = math.sqrt(xa ** 2 + ya ** 2)
        if a < tol:
            return [], []
        r = (a ** 2) / (2 * h) + h / 2
        if abs(r - a) < tol:
            b = 0
            th = 2 * math.asin(1)  # chord angle
        else:
            b = math.sqrt(r ** 2 - a ** 2)
            th = 2 * math.asin(a / r)  # chord angle

        # center of the circle
        xc = xo + b * ya / a
        yc = yo - b * xa / a

        alpha = math.atan2((y1 - yc), (x1 - xc))
        xr = []
        yr = []
        for i in range(n):
            i += 1
            dth = (i / (n + 1)) * th
            xi = xc + r * math.cos(alpha - dth)
            yi = yc + r * math.sin(alpha - dth)
            xr.append(xi)
            yr.append(yi)

        if reverse:
            xr.reverse()
            yr.reverse()
        # fmt: on
        return xr, yr

    def _get_points_for_plot(self, my_net_points):
        """Get the points to be plot
        """
        # fmt: off
        x = []
        y = []
        for i, point in enumerate(my_net_points):
            # point = my_net_points[i]
            if not point.IsArc():
                x.append(point.X.ToDouble())
                y.append(point.Y.ToDouble())
                # i += 1
            else:
                arc_h = point.GetArcHeight().ToDouble()
                p1 = [my_net_points[i - 1].X.ToDouble(), my_net_points[i - 1].Y.ToDouble()]
                if i + 1 < len(my_net_points):
                    p2 = [my_net_points[i + 1].X.ToDouble(), my_net_points[i + 1].Y.ToDouble()]
                else:
                    p2 = [my_net_points[0].X.ToDouble(), my_net_points[0].Y.ToDouble()]
                x_arc, y_arc = self._eval_arc_points(p1, p2, arc_h)
                x.extend(x_arc)
                y.extend(y_arc)
                # i += 1
        # fmt: on
        return x, y

    @pyaedt_function_handler()
    def get_plot_data(
        self,
        nets,
        layers=None,
        color_by_net=False,
        outline=None,
        plot_components_on_top=False,
        plot_components_on_bottom=False,
    ):
        """Return List of points for Matplotlib 2D Chart.

        Parameters
        ----------
        nets : str, list
            Name of the net or list of nets to plot. If `None` all nets will be plotted.
        layers : str, list, optional
            Name of the layers to include in the plot. If `None` all the signal layers will be considered.
        color_by_net : bool, optional
            If ``True``  the plot will be colored by net.
            If ``False`` the plot will be colored by layer. (default)
        outline : list, optional
            List of points of the outline to plot.
        plot_components_on_top : bool, optional
            If ``True``  the components placed on top layer are plotted.
            If ``False`` the components are not plotted. (default)
            If nets and/or layers is specified, only the components belonging to the specified nets/layers are plotted.
        plot_components_on_bottom : bool, optional
            If ``True``  the components placed on bottom layer are plotted.
            If ``False`` the components are not plotted. (default)
            If nets and/or layers is specified, only the components belonging to the specified nets/layers are plotted.

        Returns
        -------
        list, str
            list of data to be used in plot.
            In case of remote session it will be returned a string that could be converted to list
            using ast.literal_eval().
        """
        start_time = time.time()
        if not nets:
            nets = list(self.nets.keys())
        if isinstance(nets, str):
            nets = [nets]
        if not layers:
            layers = list(self._pedb.stackup.signal_layers.keys())
        if isinstance(layers, str):
            layers = [layers]
        color_index = 0
        objects_lists = []
        label_colors = {}
        n_label = 0
        max_labels = 10

        if outline:
            xt = [i[0] for i in outline]
            yt = [i[1] for i in outline]
            xc, yc = GeometryOperators.orient_polygon(xt, yt, clockwise=True)
            vertices = [(i, j) for i, j in zip(xc, yc)]
            codes = [2 for _ in vertices]
            codes[0] = 1
            vertices.append((0, 0))
            codes.append(79)
            objects_lists.append([vertices, codes, "b", "Outline", 1.0, 1.5, "contour"])
            n_label += 1
        top_layer = list(self._pedb.stackup.signal_layers.keys())[0]
        bottom_layer = list(self._pedb.stackup.signal_layers.keys())[-1]
        if plot_components_on_top or plot_components_on_bottom:
            nc = 0
            for comp in self._pedb.components.components.values():
                if not comp.is_enabled:
                    continue
                net_names = comp.nets
                if nets and not any([i in nets for i in net_names]):
                    continue
                layer_name = comp.placement_layer
                if layer_name not in layers:
                    continue
                if plot_components_on_top and layer_name == top_layer:
                    component_color = (184 / 255, 115 / 255, 51 / 255)  # this is the color used in AEDT
                    label = "Component on top layer"
                elif plot_components_on_bottom and layer_name == bottom_layer:
                    component_color = (41 / 255, 171 / 255, 135 / 255)  # 41, 171, 135
                    label = "Component on bottom layer"
                else:
                    continue
                cbb = comp.bounding_box
                x = [cbb[0], cbb[0], cbb[2], cbb[2]]
                y = [cbb[1], cbb[3], cbb[3], cbb[1]]
                vertices = [(i, j) for i, j in zip(x, y)]
                codes = [2 for _ in vertices]
                codes[0] = 1
                vertices.append((0, 0))
                codes.append(79)
                if label not in label_colors:
                    label_colors[label] = component_color
                    objects_lists.append([vertices, codes, label_colors[label], label, 1.0, 2.0, "contour"])
                    n_label += 1
                else:
                    objects_lists.append([vertices, codes, label_colors[label], None, 1.0, 2.0, "contour"])
                nc += 1
            self._logger.debug("Plotted {} component(s)".format(nc))

        for path in self._pedb.modeler.paths:
            if path.is_void:
                continue
            net_name = path.net_name
            layer_name = path.layer_name
            if nets and (net_name not in nets or layer_name not in layers):
                continue
            try:
                x, y = path.points()
            except ValueError:
                x = None
            if not x:
                continue
            create_label = False
            if not color_by_net:
                label = "Layer " + layer_name
                if label not in label_colors:
                    try:
                        color = path.layer.GetColor()
                        c = (
                            float(color.Item1 / 255),
                            float(color.Item2 / 255),
                            float(color.Item3 / 255),
                        )
                    except:
                        c = list(CSS4_COLORS.keys())[color_index]
                        color_index += 1
                        if color_index >= len(CSS4_COLORS):
                            color_index = 0
                    label_colors[label] = c
                    create_label = True
            else:
                label = "Net " + net_name
                if label not in label_colors:
                    label_colors[label] = list(CSS4_COLORS.keys())[color_index]
                    color_index += 1
                    if color_index >= len(CSS4_COLORS):
                        color_index = 0
                    create_label = True

            if create_label and n_label <= max_labels:
                objects_lists.append([x, y, label_colors[label], label, 0.4, "fill"])
                n_label += 1
            else:
                objects_lists.append([x, y, label_colors[label], None, 0.4, "fill"])

        for poly in self._pedb.modeler.polygons:
            if poly.is_void:
                continue
            net_name = poly.net_name
            layer_name = poly.layer_name
            if nets and (net_name != "" and net_name not in nets or layer_name not in layers):
                continue
            xt, yt = poly.points()
            if not xt:
                continue
            x, y = GeometryOperators.orient_polygon(xt, yt, clockwise=True)
            vertices = [(i, j) for i, j in zip(x, y)]
            codes = [2 for _ in vertices]
            codes[0] = 1
            vertices.append((0, 0))
            codes.append(79)

            for void in poly.voids:
                xvt, yvt = void.points()
                if xvt:
                    xv, yv = GeometryOperators.orient_polygon(xvt, yvt, clockwise=False)
                    tmpV = [(i, j) for i, j in zip(xv, yv)]
                    vertices.extend(tmpV)
                    tmpC = [2 for _ in tmpV]
                    tmpC[0] = 1
                    codes.extend(tmpC)
                    vertices.append((0, 0))
                    codes.append(79)

            create_label = False
            if not color_by_net:
                label = "Layer " + layer_name
                if label not in label_colors:
                    try:
                        color = poly.GetLayer().GetColor()
                        c = (
                            float(color.Item1 / 255),
                            float(color.Item2 / 255),
                            float(color.Item3 / 255),
                        )
                    except:
                        c = list(CSS4_COLORS.keys())[color_index]
                        color_index += 1
                        if color_index >= len(CSS4_COLORS):
                            color_index = 0
                    label_colors[label] = c
                    create_label = True
            else:
                label = "Net " + net_name
                if label not in label_colors:
                    label_colors[label] = list(CSS4_COLORS.keys())[color_index]
                    color_index += 1
                    if color_index >= len(CSS4_COLORS):
                        color_index = 0
                    create_label = True

            if create_label and n_label <= max_labels:
                if layer_name == "Outline":
                    objects_lists.append([vertices, codes, label_colors[label], label, 1.0, 2.0, "contour"])
                else:
                    objects_lists.append([vertices, codes, label_colors[label], label, 0.4, "path"])
                n_label += 1
            else:
                if layer_name == "Outline":
                    objects_lists.append([vertices, codes, label_colors[label], None, 1.0, 2.0, "contour"])
                else:
                    objects_lists.append([vertices, codes, label_colors[label], None, 0.4, "path"])

        for circle in self._pedb.modeler.circles:
            if circle.is_void:
                continue
            net_name = circle.net_name
            layer_name = circle.layer_name
            if nets and (net_name not in nets or layer_name not in layers):
                continue
            x, y = circle.points()
            if not x:
                continue
            create_label = False
            if not color_by_net:
                label = "Layer " + layer_name
                if label not in label_colors:
                    try:
                        color = circle.layer.GetColor()
                        c = (
                            float(color.Item1 / 255),
                            float(color.Item2 / 255),
                            float(color.Item3 / 255),
                        )
                    except:
                        c = list(CSS4_COLORS.keys())[color_index]
                        color_index += 1
                        if color_index >= len(CSS4_COLORS):
                            color_index = 0
                    label_colors[label] = c
                    create_label = True
            else:
                label = "Net " + net_name
                if label not in label_colors:
                    label_colors[label] = list(CSS4_COLORS.keys())[color_index]
                    color_index += 1
                    if color_index >= len(CSS4_COLORS):
                        color_index = 0
                    create_label = True

            if create_label and n_label <= max_labels:
                objects_lists.append([x, y, label_colors[label], label, 0.4, "fill"])
                n_label += 1
            else:
                objects_lists.append([x, y, label_colors[label], None, 0.4, "fill"])

        for rect in self._pedb.modeler.rectangles:
            if rect.is_void:
                continue
            net_name = rect.net_name
            layer_name = rect.layer_name
            if nets and (net_name not in nets or layer_name not in layers):
                continue
            x, y = rect.points()
            if not x:
                continue
            create_label = False
            if not color_by_net:
                label = "Layer " + layer_name
                if label not in label_colors:
                    try:
                        color = rect.layer.GetColor()
                        c = (
                            float(color.Item1 / 255),
                            float(color.Item2 / 255),
                            float(color.Item3 / 255),
                        )
                    except:
                        c = list(CSS4_COLORS.keys())[color_index]
                        color_index += 1
                        if color_index >= len(CSS4_COLORS):
                            color_index = 0
                    label_colors[label] = c
                    create_label = True
            else:
                label = "Net " + net_name
                if label not in label_colors:
                    label_colors[label] = list(CSS4_COLORS.keys())[color_index]
                    color_index += 1
                    if color_index >= len(CSS4_COLORS):
                        color_index = 0
                    create_label = True

            if create_label and n_label <= max_labels:
                objects_lists.append([x, y, label_colors[label], label, 0.4, "fill"])
                n_label += 1
            else:
                objects_lists.append([x, y, label_colors[label], None, 0.4, "fill"])

        end_time = time.time() - start_time
        self._logger.info("Nets Point Generation time %s seconds", round(end_time, 3))
        if os.getenv("PYAEDT_SERVER_AEDT_PATH", None):
            return str(objects_lists)
        else:
            return objects_lists

    @pyaedt_function_handler()
    def classify_nets(self, power_nets=None, signal_nets=None):
        """Reassign power/ground or signal nets based on list of nets.

        Parameters
        ----------
        power_nets : str, list, optional
            List of power nets to assign. Default is `None`.
        signal_nets : str, list, optional
            List of signal nets to assign. Default is `None`.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if isinstance(power_nets, str):
            power_nets = []
        elif not power_nets:
            power_nets = []
        if isinstance(signal_nets, str):
            signal_nets = []
        elif not signal_nets:
            signal_nets = []
        for net in power_nets:
            if net in self.nets:
                self.nets[net].net_object.SetIsPowerGround(True)
        for net in signal_nets:
            if net in self.nets:
                self.nets[net].net_object.SetIsPowerGround(False)
        return True

    @pyaedt_function_handler()
    def plot(
        self,
        nets=None,
        layers=None,
        color_by_net=False,
        show_legend=True,
        save_plot=None,
        outline=None,
        size=(2000, 1000),
        plot_components_on_top=False,
        plot_components_on_bottom=False,
    ):
        """Plot a Net to Matplotlib 2D Chart.

        Parameters
        ----------
        nets : str, list, optional
            Name of the net or list of nets to plot. If ``None`` all nets will be plotted.
        layers : str, list, optional
            Name of the layers to include in the plot. If ``None`` all the signal layers will be considered.
        color_by_net : bool, optional
            If ``True``  the plot will be colored by net.
            If ``False`` the plot will be colored by layer. (default)
        show_legend : bool, optional
            If ``True`` the legend is shown in the plot. (default)
            If ``False`` the legend is not shown.
        save_plot : str, optional
            If ``None`` the plot will be shown.
            If a file path is specified the plot will be saved to such file.
        outline : list, optional
            List of points of the outline to plot.
        size : tuple, int, optional
            Image size in pixel (width, height). Default value is ``(2000, 1000)``
        plot_components_on_top : bool, optional
            If ``True``  the components placed on top layer are plotted.
            If ``False`` the components are not plotted. (default)
            If nets and/or layers is specified, only the components belonging to the specified nets/layers are plotted.
        plot_components_on_bottom : bool, optional
            If ``True``  the components placed on bottom layer are plotted.
            If ``False`` the components are not plotted. (default)
            If nets and/or layers is specified, only the components belonging to the specified nets/layers are plotted.
        """
        if is_ironpython:
            self._logger.warning("Plot functionalities are enabled only in CPython.")
            return False
        from pyaedt.generic.plot import plot_matplotlib

        object_lists = self.get_plot_data(
            nets,
            layers,
            color_by_net,
            outline,
            plot_components_on_top,
            plot_components_on_bottom,
        )

        if isinstance(size, int):  # pragma: no cover
            board_size_x, board_size_y = self._pedb.get_statistics().layout_size
            fig_size_x = size
            fig_size_y = board_size_y * fig_size_x / board_size_x
            size = (fig_size_x, fig_size_y)

        plot_matplotlib(
            plot_data=object_lists,
            size=size,
            show_legend=show_legend,
            xlabel="X (m)",
            ylabel="Y (m)",
            title=self._pedb.active_cell.GetName(),
            snapshot_path=save_plot,
            axis_equal=True,
        )

    @pyaedt_function_handler()
    def is_power_gound_net(self, netname_list):
        """Determine if one of the  nets in a list is power or ground.

        Parameters
        ----------
        netname_list : list
            List of net names.

        Returns
        -------
        bool
            ``True`` when one of the net names is ``"power"`` or ``"ground"``, ``False`` otherwise.
        """
        if isinstance(netname_list, str):
            netname_list = [netname_list]
        power_nets_names = list(self.power_nets.keys())
        for netname in netname_list:
            if netname in power_nets_names:
                return True
        return False

    @pyaedt_function_handler()
    def get_dcconnected_net_list(self, ground_nets=["GND"], res_value=0.001):
        """Get the nets connected to the direct current through inductors.

        .. note::
           Only inductors are considered.

        Parameters
        ----------
        ground_nets : list, optional
            List of ground nets. The default is ``["GND"]``.

        Returns
        -------
        list
            List of nets connected to DC through inductors.
        """
        temp_list = []
        for _, comp_obj in self._pedb.components.inductors.items():
            numpins = comp_obj.numpins

            if numpins == 2:
                nets = comp_obj.nets
                if not set(nets).intersection(set(ground_nets)):
                    temp_list.append(set(nets))
                else:
                    pass
        for _, comp_obj in self._pedb.components.resistors.items():
            numpins = comp_obj.numpins

            if numpins == 2 and self._pedb._decompose_variable_value(comp_obj.res_value) <= res_value:
                nets = comp_obj.nets
                if not set(nets).intersection(set(ground_nets)):
                    temp_list.append(set(nets))
                else:
                    pass
        dcconnected_net_list = []

        while not not temp_list:
            s = temp_list.pop(0)
            interseciton_flag = False
            for i in temp_list:
                if not not s.intersection(i):
                    i.update(s)
                    interseciton_flag = True

            if not interseciton_flag:
                dcconnected_net_list.append(s)

        return dcconnected_net_list

    @pyaedt_function_handler()
    def get_powertree(self, power_net_name, ground_nets):
        """Retrieve the power tree.

        Parameters
        ----------
        power_net_name : str
            Name of the power net.
        ground_nets :


        Returns
        -------

        """
        flag_in_ng = False
        net_group = []
        for ng in self.get_dcconnected_net_list(ground_nets):
            if power_net_name in ng:
                flag_in_ng = True
                net_group.extend(ng)
                break

        if not flag_in_ng:
            net_group.append(power_net_name)

        component_list = []
        rats = self._pedb.components.get_rats()
        for net in net_group:
            for el in rats:
                if net in el["net_name"]:
                    i = 0
                    for n in el["net_name"]:
                        if n == net:
                            df = [el["refdes"][i], el["pin_name"][i], net]
                            component_list.append(df)
                        i += 1

        component_type = []
        for el in component_list:
            refdes = el[0]
            comp_type = self._pedb.components._cmp[refdes].type
            component_type.append(comp_type)
            el.append(comp_type)

            comp_partname = self._pedb.components._cmp[refdes].partname
            el.append(comp_partname)
            pins = self._pedb.components.get_pin_from_component(component=refdes, netName=el[2])
            el.append("-".join([i.GetName() for i in pins]))

        component_list_columns = [
            "refdes",
            "pin_name",
            "net_name",
            "component_type",
            "component_partname",
            "pin_list",
        ]
        return component_list, component_list_columns, net_group

    @pyaedt_function_handler()
    def get_net_by_name(self, net_name):
        """Find a net by name."""
        edb_net = self._edb.cell.net.find_by_name(self._active_layout, net_name)
        if edb_net is not None:
            return edb_net

    @pyaedt_function_handler()
    def delete_nets(self, netlist):
        """Delete one or more nets from EDB.

        .. deprecated:: 0.6.62
           Use :func:`delete` method instead.

        Parameters
        ----------
        netlist : str or list
            One or more nets to delete.

        Returns
        -------
        list
            List of nets that were deleted.

        Examples
        --------
        >>> deleted_nets = edb_core.nets.delete(["Net1","Net2"])
        """
        warnings.warn("Use :func:`delete` method instead.", DeprecationWarning)
        return self.delete(netlist=netlist)

    @pyaedt_function_handler()
    def delete(self, netlist):
        """Delete one or more nets from EDB.

        Parameters
        ----------
        netlist : str or list
            One or more nets to delete.

        Returns
        -------
        list
            List of nets that were deleted.

        Examples
        --------
        >>> deleted_nets = edb_core.nets.delete(["Net1","Net2"])
        """
        if isinstance(netlist, str):
            netlist = [netlist]

        self._pedb.modeler.delete_primitives(netlist)
        self._pedb.padstacks.delete_padstack_instances(netlist)

        nets_deleted = []

        for i in self._pedb.nets.nets.values():
            if i.name in netlist:
                i.net_object.Delete()
                nets_deleted.append(i.name)
        return nets_deleted

    @pyaedt_function_handler()
    def find_or_create_net(self, net_name="", start_with="", contain="", end_with=""):
        """Find or create the net with the given name in the layout.

        Parameters
        ----------
        net_name : str, optional
            Name of the net to find or create. The default is ``""``.

        start_with : str, optional
            All net name starting with the string. Not case-sensitive.

        contain : str, optional
            All net name containing the string. Not case-sensitive.

        end_with : str, optional
            All net name ending with the string. Not case-sensitive.

        Returns
        -------
        object
            Net Object.
        """
        if not net_name and not start_with and not contain and not end_with:
            net_name = generate_unique_name("NET_")
            net = self._edb.cell.net.create(self._active_layout, net_name)
            return net
        else:
            if not start_with and not contain and not end_with:
                net = self._edb.cell.net.find_by_name(self._active_layout, net_name)
                if net.IsNull():
                    net = self._edb.cell.net.create(self._active_layout, net_name)
                return net
            elif start_with:
                nets_found = [
                    self.nets[net].net_object for net in list(self.nets.keys()) if net.lower().startswith(start_with)
                ]
                return nets_found
            elif start_with and end_with:
                nets_found = [
                    self.nets[net].net_object
                    for net in list(self.nets.keys())
                    if net.lower().startswith(start_with) and net.lower().endswith(end_with)
                ]
                return nets_found
            elif start_with and contain and end_with:
                nets_found = [
                    self.nets[net].net_object
                    for net in list(self.nets.keys())
                    if net.lower().startswith(start_with) and net.lower().endswith(end_with) and contain in net.lower()
                ]
                return nets_found
            elif start_with and contain:
                nets_found = [
                    self.nets[net].net_object
                    for net in list(self.nets.keys())
                    if net.lower().startswith(start_with) and contain in net.lower()
                ]
                return nets_found
            elif contain and end_with:
                nets_found = [
                    self.nets[net].net_object
                    for net in list(self.nets.keys())
                    if net.lower().endswith(end_with) and contain in net.lower()
                ]
                return nets_found
            elif end_with and not start_with and not contain:
                nets_found = [
                    self.nets[net].net_object for net in list(self.nets.keys()) if net.lower().endswith(end_with)
                ]
                return nets_found
            elif contain and not start_with and not end_with:
                nets_found = [self.nets[net].net_object for net in list(self.nets.keys()) if contain in net.lower()]
                return nets_found

    @pyaedt_function_handler()
    def is_net_in_component(self, component_name, net_name):
        """Check if a net belongs to a component.

        Parameters
        ----------
        component_name : str
            Name of the component.
        net_name : str
            Name of the net.

        Returns
        -------
        bool
            ``True`` if the net is found in component pins.

        """
        if component_name not in self._pedb.components.components:
            return False
        for net in self._pedb.components.components[component_name].nets:
            if net_name == net:
                return True
        return False

    @pyaedt_function_handler()
    def find_and_fix_disjoint_nets(
        self, net_list=None, keep_only_main_net=False, clean_disjoints_less_than=0.0, order_by_area=False
    ):
        """Find and fix disjoint nets from a given netlist.

        .. deprecated::
           Use new property :func:`edb.layout_validation.disjoint_nets` instead.

        Parameters
        ----------
        net_list : str, list, optional
            List of nets on which check disjoints. If `None` is provided then the algorithm will loop on all nets.
        keep_only_main_net : bool, optional
            Remove all secondary nets other than principal one (the one with more objects in it). Default is `False`.
        clean_disjoints_less_than : bool, optional
            Clean all disjoint nets with area less than specified area in square meters. Default is `0.0` to disable it.
        order_by_area : bool, optional
            Whether if the naming order has to be by number of objects (fastest) or area (slowest but more accurate).
            Default is ``False``.

        Returns
        -------
        List
            New nets created.

        Examples
        --------
        >>> renamed_nets = edb_core.nets.find_and_fix_disjoint_nets(["GND","Net2"])
        """
        warnings.warn("Use new function :func:`edb.layout_validation.disjoint_nets` instead.", DeprecationWarning)
        return self._pedb.layout_validation.disjoint_nets(
            net_list, keep_only_main_net, clean_disjoints_less_than, order_by_area
        )

    @pyaedt_function_handler()
    def merge_nets_polygons(self, net_list):
        """Convert paths from net into polygons, evaluate all connected polygons and perform the merge.

        Parameters
        ----------
        net_list : str or list[str]
            net name of list of net name.

        Returns
        -------
            list of merged polygons.

        -------

        """
        if isinstance(net_list, str):
            net_list = [net_list]
        returned_poly = []
        for net in net_list:
            if net in self.nets:
                net_rtree = self._edb.Geometry.RTree()
                paths = [prim for prim in self.nets[net].primitives if prim.type == "Path"]
                for path in paths:
                    path.convert_to_polygon()
                polygons = [prim for prim in self.nets[net].primitives if prim.type == "Polygon"]
                for polygon in polygons:
                    polygon_data = polygon.primitive_object.GetPolygonData()
                    rtree = self._edb.Geometry.RTreeObj(polygon_data, polygon.primitive_object)
                    net_rtree.Insert(rtree)
                connected_polygons = net_rtree.GetConnectedGeometrySets()
                void_list = []
                for pp in list(connected_polygons):
                    for _pp in list(pp):
                        _voids = list(_pp.Obj.Voids)
                        void_list.extend(_pp.Obj.Voids)
                for poly_list in list(connected_polygons):
                    layer = list(poly_list)[0].Obj.GetLayer().GetName()
                    net = list(poly_list)[0].Obj.GetNet()
                    _poly_list = convert_py_list_to_net_list([obj.Poly for obj in list(poly_list)])
                    merged_polygon = list(self._edb.geometry.polygon_data.unite(_poly_list))
                    for poly in merged_polygon:
                        for void in void_list:
                            poly.AddHole(void.GetPolygonData())
                        _new_poly = self._edb.cell.primitive.polygon.create(self._active_layout, layer, net, poly)
                        returned_poly.append(_new_poly)
                for init_poly in list(list(connected_polygons)):
                    for _pp in list(init_poly):
                        _pp.Obj.Delete()
        return returned_poly
