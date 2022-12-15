from __future__ import absolute_import  # noreorder

import math
import os
import time

from pyaedt.edb_core.edb_data.nets_data import EDBNetsData
from pyaedt.edb_core.edb_data.padstacks_data import EDBPadstackInstance
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.generic.constants import CSS4_COLORS
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import is_ironpython
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.generic.plot import plot_matplotlib
from pyaedt.modeler.GeometryOperators import GeometryOperators


class EdbNets(object):
    """Manages EDB methods for nets management accessible from `Edb.core_nets` property.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edbapp = Edb("myaedbfolder", edbversion="2021.2")
    >>> edb_nets = edbapp.core_nets
    """

    def __init__(self, p_edb):
        self._pedb = p_edb

    @property
    def _builder(self):
        """ """
        return self._pedb.builder

    @property
    def _edb(self):
        """ """
        return self._pedb.edb

    @property
    def _active_layout(self):
        """ """
        return self._pedb.active_layout

    @property
    def _cell(self):
        """ """
        return self._pedb.cell

    @property
    def db(self):
        """Db object."""
        return self._pedb.db

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
        nets = {}
        for net in self._active_layout.Nets:
            nets[net.GetName()] = EDBNetsData(net, self._pedb)
        return nets

    @property
    def signal_nets(self):
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
    def power_nets(self):
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

    @property
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
        nets = list(self._active_layout.Nets)
        for net in nets:
            total_plane_area = 0.0
            total_trace_area = 0.0
            for primitive in net.Primitives:
                if primitive.GetPrimitiveType() == self._edb.Cell.Primitive.PrimitiveType.Bondwire:
                    continue
                if primitive.GetPrimitiveType() != self._edb.Cell.Primitive.PrimitiveType.Path:
                    total_plane_area += float(primitive.GetPolygonData().Area())
                else:
                    total_trace_area += float(primitive.GetPolygonData().Area())
            if total_plane_area == 0.0:
                continue
            if total_trace_area == 0.0:
                pwr_gnd_nets.append(EDBNetsData(net, self._pedb))
                continue
            if total_plane_area > 0.0 and total_trace_area > 0.0:
                if total_plane_area / (total_plane_area + total_trace_area) > threshold:
                    pwr_gnd_nets.append(EDBNetsData(net, self._pedb))
        return pwr_gnd_nets

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
        xa = (x2-x1) / 2
        ya = (y2-y1) / 2
        xo = x1 + xa
        yo = y1 + ya
        a = math.sqrt(xa**2 + ya**2)
        if a < tol:
            return [], []
        r = (a**2)/(2*h) + h/2
        if abs(r-a) < tol:
            b = 0
            th = 2 * math.asin(1)  # chord angle
        else:
            b = math.sqrt(r**2 - a**2)
            th = 2 * math.asin(a/r)  # chord angle

        # center of the circle
        xc = xo + b*ya/a
        yc = yo - b*xa/a

        alpha = math.atan2((y1-yc), (x1-xc))
        xr = []
        yr = []
        for i in range(n):
            i += 1
            dth = (i/(n+1)) * th
            xi = xc + r * math.cos(alpha-dth)
            yi = yc + r * math.sin(alpha-dth)
            xr.append(xi)
            yr.append(yi)

        if reverse:
            xr.reverse()
            yr.reverse()
        # fmt: on
        return xr, yr

    def _get_points_for_plot(self, my_net_points):
        """
        Get the points to be plot
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
                p1 = [my_net_points[i-1].X.ToDouble(), my_net_points[i-1].Y.ToDouble()]
                if i+1 < len(my_net_points):
                    p2 = [my_net_points[i+1].X.ToDouble(), my_net_points[i+1].Y.ToDouble()]
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
        top_layer = list(self._pedb.stackup.signal_layers.keys())[-1]
        bottom_layer = list(self._pedb.stackup.signal_layers.keys())[0]
        if plot_components_on_top or plot_components_on_bottom:
            nc = 0
            for comp in self._pedb.core_components.components.values():
                if not comp.is_enabled:
                    continue
                net_names = comp.nets
                if not any([i in nets for i in net_names]):
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

        for path in self._pedb.core_primitives.paths:
            if path.is_void:
                continue
            net_name = path.net_name
            layer_name = path.layer_name
            if net_name not in nets or layer_name not in layers:
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

        for poly in self._pedb.core_primitives.polygons:
            if poly.is_void:
                continue
            net_name = poly.net_name
            layer_name = poly.layer_name
            if net_name not in nets or layer_name not in layers:
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
                objects_lists.append([vertices, codes, label_colors[label], label, 0.4, "path"])
                n_label += 1
            else:
                objects_lists.append([vertices, codes, label_colors[label], None, 0.4, "path"])

        for circle in self._pedb.core_primitives.circles:
            if circle.is_void:
                continue
            net_name = circle.net_name
            layer_name = circle.layer_name
            if net_name not in nets or layer_name not in layers:
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

        for rect in self._pedb.core_primitives.rectangles:
            if rect.is_void:
                continue
            net_name = rect.net_name
            layer_name = rect.layer_name
            if net_name not in nets or layer_name not in layers:
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
        nets,
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
        nets : str, list
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
        size : tuple, optional
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
        object_lists = self.get_plot_data(
            nets,
            layers,
            color_by_net,
            outline,
            plot_components_on_top,
            plot_components_on_bottom,
        )
        plot_matplotlib(
            object_lists,
            size,
            show_legend,
            "X (m)",
            "Y (m)",
            self._pedb.active_cell.GetName(),
            save_plot,
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
    def get_dcconnected_net_list(self, ground_nets=["GND"]):
        """Retrieve the nets connected to DC through inductors.

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
        for refdes, comp_obj in self._pedb.core_components.inductors.items():

            numpins = comp_obj.numpins

            if numpins == 2:
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
        rats = self._pedb.core_components.get_rats()
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
            comp_type = self._pedb.core_components._cmp[refdes].type
            component_type.append(comp_type)
            el.append(comp_type)

            comp_partname = self._pedb.core_components._cmp[refdes].partname
            el.append(comp_partname)
            pins = self._pedb.core_components.get_pin_from_component(component=refdes, netName=el[2])
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
        edb_net = self._edb.Cell.Net.FindByName(self._active_layout, net_name)
        if edb_net is not None:
            return edb_net

    @pyaedt_function_handler()
    def delete_nets(self, netlist):
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

        >>> deleted_nets = edb_core.core_nets.delete_nets(["Net1","Net2"])
        """
        if isinstance(netlist, str):
            netlist = [netlist]

        self._pedb.core_primitives.delete_primitives(netlist)
        self._pedb.core_padstack.delete_padstack_instances(netlist)

        nets_deleted = []

        for i in self._pedb.core_nets.nets.values():
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
            Net Object
        """
        if not net_name and not start_with and not contain and not end_with:
            net_name = generate_unique_name("NET_")
            net = self._edb.Cell.Net.Create(self._active_layout, net_name)
            return net
        else:
            if not start_with and not contain and not end_with:
                net = self._edb.Cell.Net.FindByName(self._active_layout, net_name)
                if net.IsNull():
                    net = self._edb.Cell.Net.Create(self._active_layout, net_name)
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
        if component_name not in self._pedb.core_components.components:
            return False
        for net in self._pedb.core_components.components[component_name].nets:
            if net_name == net:
                return True
        return False

    @pyaedt_function_handler()
    def find_and_fix_disjoint_nets(self, net_list=None, keep_only_main_net=False, clean_disjoints_less_than=0.0):
        """Find and fix disjoint nets from a given netlist.

        Parameters
        ----------
        net_list : str, list, optional
            List of nets on which check disjoints. If `None` is provided then the algorithm will loop on all nets.
        keep_only_main_net : bool, optional
            Remove all secondary nets other than principal one (the one with more objects in it). Default is `False`.
        clean_disjoints_less_than : bool, optional
            Clean all disjoint nets with area less than specified area in square meters. Default is `0.0` to disable it.

        Returns
        -------
        List
            New nets created.

        Examples
        --------

        >>> renamed_nets = edb_core.core_nets.find_and_fix_disjoint_nets(["GND","Net2"])
        """
        timer_start = self._logger.reset_timer()

        if not net_list:
            net_list = list(self.nets.keys())
        elif isinstance(net_list, str):
            net_list = [net_list]
        _objects_list = {}
        _padstacks_list = {}
        for prim in self._pedb.core_primitives.primitives:
            n_name = prim.net_name
            if n_name in _objects_list:
                _objects_list[n_name].append(prim)
            else:
                _objects_list[n_name] = [prim]
        for pad in list(self._pedb.core_padstack.padstack_instances.values()):
            n_name = pad.net_name
            if n_name in _padstacks_list:
                _padstacks_list[n_name].append(pad)
            else:
                _padstacks_list[n_name] = [pad]
        new_nets = []
        disjoints_objects = []
        self._logger.reset_timer()
        for net in net_list:
            net_groups = []
            obj_dict = {}
            for i in _objects_list.get(net, []):
                obj_dict[i.id] = i
            for i in _padstacks_list.get(net, []):
                obj_dict[i.id] = i
            objs = list(obj_dict.values())
            l = len(objs)
            while l > 0:
                l1 = objs[0].get_connected_object_id_set()
                l1.append(objs[0].id)
                net_groups.append(l1)
                objs = [i for i in objs if i.id not in l1]
                l = len(objs)
            if len(net_groups) > 1:
                sorted_list = sorted(net_groups, key=len, reverse=True)
                for disjoints in sorted_list[1:]:
                    if keep_only_main_net:
                        for geo in disjoints:
                            try:
                                obj_dict[geo].delete()
                            except KeyError:
                                pass
                    elif len(disjoints) == 1 and (
                        isinstance(obj_dict[disjoints[0]], EDBPadstackInstance)
                        or (clean_disjoints_less_than and obj_dict[disjoints[0]].area() < clean_disjoints_less_than)
                    ):
                        try:
                            obj_dict[disjoints[0]].delete()
                        except KeyError:
                            pass
                    else:
                        new_net_name = generate_unique_name(net, n=6)
                        net_obj = self.find_or_create_net(new_net_name)
                        if net_obj:
                            new_nets.append(net_obj.GetName())
                            for geo in disjoints:
                                try:
                                    obj_dict[geo].net_name = net_obj
                                except KeyError:
                                    pass
                            disjoints_objects.extend(disjoints)
        self._logger.info("Found {} objects in {} new nets.".format(len(disjoints_objects), len(new_nets)))
        self._logger.info_timer("Disjoint Cleanup Completed.", timer_start)

        return new_nets

    @pyaedt_function_handler()
    def merge_nets_polygons(self, net_list):
        """Convert paths from net into polygons, evaluate all connected polygons and perform the merge.

        Parameters
        ----------
        net_list : str or list[str]
            net name of list of net name.

        Returns
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
                    merged_polygon = list(self._edb.Geometry.PolygonData.Unite(_poly_list))
                    for poly in merged_polygon:
                        for void in void_list:
                            poly.AddHole(void.GetPolygonData())
                        _new_poly = self._edb.Cell.Primitive.Polygon.Create(self._active_layout, layer, net, poly)
                        returned_poly.append(_new_poly)
                for init_poly in list(list(connected_polygons)):
                    for _pp in list(init_poly):
                        _pp.Obj.Delete()
        return returned_poly
