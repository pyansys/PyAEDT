import ast
from collections import defaultdict
import csv
from datetime import datetime
import math
import os
import tempfile
import time
import warnings

from pyaedt import pyaedt_function_handler
from pyaedt.generic.constants import AEDT_UNITS, CSS4_COLORS
from pyaedt.generic.general_methods import is_ironpython, open_file

if not is_ironpython:
    try:
        import numpy as np
    except ImportError:
        warnings.warn(
            "The NumPy module is required to run some functionalities of PostProcess.\n"
            "Install with \n\npip install numpy\n\nRequires CPython."
        )

    try:
        import pyvista as pv

        pyvista_available = True
    except ImportError:
        warnings.warn(
            "The PyVista module is required to run some functionalities of PostProcess.\n"
            "Install with \n\npip install pyvista\n\nRequires CPython."
        )

    try:
        from matplotlib.patches import PathPatch
        from matplotlib.path import Path
        import matplotlib.pyplot as plt

    except ImportError:
        warnings.warn(
            "The Matplotlib module is required to run some functionalities of PostProcess.\n"
            "Install with \n\npip install matplotlib\n\nRequires CPython."
        )
    except:
        pass


@pyaedt_function_handler()
def get_structured_mesh(theta, phi, ff_data):
    if ff_data.min() < 0:
        ff_data_renorm = ff_data + np.abs(ff_data.min())
    else:
        ff_data_renorm = ff_data
    phi_grid, theta_grid = np.meshgrid(phi, theta)
    r_no_renorm = np.reshape(ff_data, (len(theta), len(phi)))
    r = np.reshape(ff_data_renorm, (len(theta), len(phi)))

    x = r * np.sin(theta_grid) * np.cos(phi_grid)
    y = r * np.sin(theta_grid) * np.sin(phi_grid)
    z = r * np.cos(theta_grid)

    mag = np.ndarray.flatten(r_no_renorm, order="F")
    ff_mesh = pv.StructuredGrid(x, y, z)
    ff_mesh["FarFieldData"] = mag
    return ff_mesh


def is_notebook():
    """Check if pyaedt is running in Jupyter or not.

    Returns
    -------
    bool
    """
    try:
        shell = get_ipython().__class__.__name__
        if shell == "ZMQInteractiveShell":
            return True  # Jupyter notebook or qtconsole
        else:
            return False
    except NameError:
        return False  # Probably standard Python interpreter


def is_float(istring):
    """Convert a string to a float.

    Parameters
    ----------
    istring : str
        String to convert to a float.

    Returns
    -------
    float
        Converted float when successful, ``0`` when when failed.
    """
    try:
        return float(istring.strip())
    except Exception:
        return 0


def _triangle_vertex(elements_nodes, num_nodes_per_element, take_all_nodes=True):
    trg_vertex = []
    if num_nodes_per_element == 10 and take_all_nodes:
        for e in elements_nodes:
            trg_vertex.append([e[0], e[1], e[3]])
            trg_vertex.append([e[1], e[2], e[4]])
            trg_vertex.append([e[1], e[4], e[3]])
            trg_vertex.append([e[3], e[4], e[5]])

            trg_vertex.append([e[9], e[6], e[8]])
            trg_vertex.append([e[6], e[0], e[3]])
            trg_vertex.append([e[6], e[3], e[8]])
            trg_vertex.append([e[8], e[3], e[5]])

            trg_vertex.append([e[9], e[7], e[8]])
            trg_vertex.append([e[7], e[2], e[4]])
            trg_vertex.append([e[7], e[4], e[8]])
            trg_vertex.append([e[8], e[4], e[5]])

            trg_vertex.append([e[9], e[7], e[6]])
            trg_vertex.append([e[7], e[2], e[1]])
            trg_vertex.append([e[7], e[1], e[6]])
            trg_vertex.append([e[6], e[1], e[0]])

    elif num_nodes_per_element == 10 and not take_all_nodes:
        for e in elements_nodes:
            trg_vertex.append([e[0], e[2], e[5]])
            trg_vertex.append([e[9], e[0], e[5]])
            trg_vertex.append([e[9], e[2], e[0]])
            trg_vertex.append([e[9], e[2], e[5]])

    elif num_nodes_per_element == 6 and not take_all_nodes:
        for e in elements_nodes:
            trg_vertex.append([e[0], e[2], e[5]])

    elif num_nodes_per_element == 6 and take_all_nodes:
        for e in elements_nodes:
            trg_vertex.append([e[0], e[1], e[3]])
            trg_vertex.append([e[1], e[2], e[4]])
            trg_vertex.append([e[1], e[4], e[3]])
            trg_vertex.append([e[3], e[4], e[5]])

    elif num_nodes_per_element == 4 and take_all_nodes:
        for e in elements_nodes:
            trg_vertex.append([e[0], e[1], e[3]])
            trg_vertex.append([e[1], e[2], e[3]])
            trg_vertex.append([e[0], e[1], e[2]])
            trg_vertex.append([e[0], e[2], e[3]])

    elif num_nodes_per_element == 3:
        trg_vertex = elements_nodes

    return trg_vertex


def _parse_aedtplt(filepath):
    lines = []
    vertices = []
    faces = []
    scalars = []
    with open_file(filepath, "r") as f:
        drawing_found = False
        for line in f:
            if "$begin Drawing" in line:
                drawing_found = True
                l_tmp = []
                continue
            if "$end Drawing" in line:
                lines.append(l_tmp)
                drawing_found = False
                continue
            if drawing_found:
                l_tmp.append(line)
                continue
    for drawing_lines in lines:
        bounding = []
        elements = []
        nodes_list = []
        solution = []
        for l in drawing_lines:
            if "BoundingBox(" in l:
                bounding = l[l.find("(") + 1 : -2].split(",")
                bounding = [i.strip() for i in bounding]
            if "Elements(" in l:
                elements = l[l.find("(") + 1 : -2].split(",")
                elements = [int(i.strip()) for i in elements]
            if "Nodes(" in l:
                nodes_list = l[l.find("(") + 1 : -2].split(",")
                nodes_list = [float(i.strip()) for i in nodes_list]
            if "ElemSolution(" in l:
                # convert list of strings to list of floats
                sols = l[l.find("(") + 1 : -2].split(",")
                sols = [is_float(value) for value in sols]
                # sols = [float(i.strip()) for i in sols]
                num_solution_per_element = int(sols[2])
                num_elements = elements[1]
                num_nodes = elements[6]
                sols = sols[3:]
                if num_nodes == num_solution_per_element or num_solution_per_element // num_nodes < 3:
                    sols = [
                        sols[i : i + num_solution_per_element] for i in range(0, len(sols), num_solution_per_element)
                    ]
                    solution = [sum(i) / num_solution_per_element for i in sols]
                else:
                    sols = [
                        sols[i : i + num_solution_per_element] for i in range(0, len(sols), num_solution_per_element)
                    ]
                    solution = [
                        [sum(i[::3]) / num_solution_per_element * 3 for i in sols],
                        [sum(i[1::3]) / num_solution_per_element * 3 for i in sols],
                        [sum(i[2::3]) / num_solution_per_element * 3 for i in sols],
                    ]

        nodes = [[nodes_list[i], nodes_list[i + 1], nodes_list[i + 2]] for i in range(0, len(nodes_list), 3)]
        num_nodes = elements[0]
        num_elements = elements[1]
        elements = elements[2:]
        element_type = elements[0]
        num_nodes_per_element = elements[4]
        header_length = 5
        elements_nodes = []
        # Todo Aedt 23R2 supports mixed elements size. To be implemented.
        for i in range(0, len(elements), num_nodes_per_element + header_length):
            elements_nodes.append([elements[i + header_length + n] for n in range(num_nodes_per_element)])
        if solution:
            take_all_nodes = True  # solution case
        else:
            take_all_nodes = False  # mesh case
        trg_vertex = _triangle_vertex(elements_nodes, num_nodes_per_element, take_all_nodes)
        # remove duplicates
        nodup_list = [list(i) for i in list(set([frozenset(t) for t in trg_vertex]))]
        log = True
        if solution:
            if isinstance(solution[0], list):
                temps = []
                for sol in solution:
                    sv = {}
                    sv_i = {}
                    sv = defaultdict(lambda: 0, sv)
                    sv_i = defaultdict(lambda: 1, sv_i)
                    for els, s in zip(elements_nodes, sol):
                        for el in els:
                            sv[el] = (sv[el] + s) / sv_i[el]
                            sv_i[el] = 2
                    temps.append(np.array([sv[v] for v in sorted(sv.keys())]))
            else:
                sv = {}
                sv_i = {}
                sv = defaultdict(lambda: 0, sv)
                sv_i = defaultdict(lambda: 1, sv_i)

                for els, s in zip(elements_nodes, solution):
                    for el in els:
                        sv[el] = (sv[el] + s) / sv_i[el]
                        sv_i[el] = 2
                temps = np.array([sv[v] for v in sorted(sv.keys())])
            scalars.append(temps)
            if np.min(temps) <= 0:
                log = False
        array = [[3] + [j - 1 for j in i] for i in nodup_list]

        faces.append(np.hstack(array))
        vertices.append(np.array(nodes))
        # surf = pv.PolyData(vertices, faces)

        # surf.point_data[field.label] = temps
    # field.log = log
    # field._cached_polydata = surf
    return vertices, faces, scalars, log


def _parse_streamline(filepath):
    streamlines = []
    with open_file(filepath, "r") as f:
        lines = f.read().splitlines()
        new_line = False
        streamline = []
        for line in lines:
            if "Streamline: " in line:
                new_line = True
                if streamline:
                    streamlines.append(streamline)
                    streamline = []

            elif new_line:
                streamline.append(line.split(" "))
    return streamlines


@pyaedt_function_handler()
def plot_polar_chart(
    plot_data, size=(2000, 1000), show_legend=True, xlabel="", ylabel="", title="", snapshot_path=None
):
    """Create a matplotlib polar plot based on a list of data.

    Parameters
    ----------
    plot_data : list of list
        List of plot data. Every item has to be in the following format
        `[x points, y points, label]`.
    size : tuple, optional
        Image size in pixel (width, height).
    show_legend : bool
        Either to show legend or not.
    xlabel : str
        Plot X label.
    ylabel : str
        Plot Y label.
    title : str
        Plot Title label.
    snapshot_path : str
        Full path to image file if a snapshot is needed.
    """
    dpi = 100.0

    ax = plt.subplot(111, projection="polar")

    label_id = 1
    legend = []
    for object in plot_data:
        if len(object) == 3:
            label = object[2]
        else:
            label = "Trace " + str(label_id)
        theta = np.array(object[0])
        r = np.array(object[1])
        ax.plot(theta, r)
        ax.grid(True)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        legend.append(label)
        label_id += 1

    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    if show_legend:
        ax.legend(legend)

    fig = plt.gcf()
    fig.set_size_inches(size[0] / dpi, size[1] / dpi)
    if snapshot_path:
        fig.savefig(snapshot_path)
    else:
        fig.show()
    return fig


@pyaedt_function_handler()
def plot_3d_chart(plot_data, size=(2000, 1000), xlabel="", ylabel="", title="", snapshot_path=None):
    """Create a matplotlib 3D plot based on a list of data.

    Parameters
    ----------
    plot_data : list of list
        List of plot data. Every item has to be in the following format
        `[x points, y points, z points, label]`.
    size : tuple, optional
        Image size in pixel (width, height).
    xlabel : str
        Plot X label.
    ylabel : str
        Plot Y label.
    title : str
        Plot Title label.
    snapshot_path : str
        Full path to image file if a snapshot is needed.

    Returns
    -------
    :class:`matplotlib.plt`
        Matplotlib fig object.
    """
    dpi = 100.0

    ax = plt.subplot(111, projection="3d")

    if isinstance(plot_data[0], np.ndarray):
        x = plot_data[0]
        y = plot_data[1]
        z = plot_data[2]
    else:
        theta_grid, phi_grid = np.meshgrid(plot_data[0], plot_data[1])
        if isinstance(plot_data[2], list):
            r = np.array(plot_data[2])
        else:
            r = plot_data[2]
        x = r * np.sin(theta_grid) * np.cos(phi_grid)
        y = r * np.sin(theta_grid) * np.sin(phi_grid)
        z = r * np.cos(theta_grid)
    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    ax.plot_surface(x, y, z, rstride=1, cstride=1, cmap=plt.get_cmap("jet"), linewidth=0, antialiased=True, alpha=0.8)
    fig = plt.gcf()
    fig.set_size_inches(size[0] / dpi, size[1] / dpi)
    if snapshot_path:
        fig.savefig(snapshot_path)
    else:
        fig.show()
    return fig


@pyaedt_function_handler()
def plot_2d_chart(plot_data, size=(2000, 1000), show_legend=True, xlabel="", ylabel="", title="", snapshot_path=None):
    """Create a matplotlib plot based on a list of data.

    Parameters
    ----------
    plot_data : list of list
        List of plot data. Every item has to be in the following format
        `[x points, y points, label]`.
    size : tuple, optional
        Image size in pixel (width, height).
    show_legend : bool, optional
        Either to show legend or not. The default value is ``True``.
    xlabel : str, optional
        Plot X label. The default value is ``""``.
    ylabel : str, optional
        Plot Y label. The default value is ``""``.
    title : str, optional
        Plot Title label. The default value is ``""``.
    snapshot_path : str, optional
        Full path to image file if a snapshot is needed.
        The default value is ``None``.

    Returns
    -------
    :class:`matplotlib.plt`
        Matplotlib fig object.
    """
    dpi = 100.0
    figsize = (size[0] / dpi, size[1] / dpi)
    fig, ax = plt.subplots(figsize=figsize)
    label_id = 1
    for plo_obj in plot_data:
        if len(plo_obj) == 3:
            label = plo_obj[2]
        else:
            label = "Trace " + str(label_id)
        if isinstance(plo_obj[0], np.ndarray):
            x = plo_obj[0]
            y = plo_obj[1]
        else:
            x = np.array([i for i, j in zip(plo_obj[0], plo_obj[1]) if j])
            y = np.array([i for i in plo_obj[1] if i])
        ax.plot(x, y, label=label)
        label_id += 1

    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    if show_legend:
        ax.legend()

    if snapshot_path:
        fig.savefig(snapshot_path)
    elif not is_notebook():
        fig.show()
    return fig


@pyaedt_function_handler()
def plot_matplotlib(
    plot_data,
    size=(2000, 1000),
    show_legend=True,
    xlabel="",
    ylabel="",
    title="",
    snapshot_path=None,
    x_limits=None,
    y_limits=None,
    axis_equal=False,
    annotations=None,
    show=True,
):
    """Create a matplotlib plot based on a list of data.

    Parameters
    ----------
    plot_data : list of list
        List of plot data. Every item has to be in the following format
        For type ``fill``: `[x points, y points, color, label, alpha, type=="fill"]`.
        For type ``path``: `[vertices, codes, color, label, alpha, type=="path"]`.
        For type ``contour``: `[vertices, codes, color, label, alpha, line_width, type=="contour"]`.
    size : tuple, optional
        Image size in pixel (width, height). Default is `(2000, 1000)`.
    show_legend : bool, optional
        Either to show legend or not. Default is `True`.
    xlabel : str, optional
        Plot X label. Default is `""`.
    ylabel : str, optional
        Plot Y label. Default is `""`.
    title : str, optional
        Plot Title label. Default is `""`.
    snapshot_path : str, optional
        Full path to image file if a snapshot is needed. Default is `None`.
    x_limits : list, optional
        List of x limits (left and right). Default is `None`.
    y_limits : list, optional
        List of y limits (bottom and top). Default is `None`.
    axis_equal : bool, optional
         Whether to show the same scale on both axis or have a different scale based on plot size.
        Default is `False`.
    annotations : list, optional
        List of annotations to add to the plot. The format is [x, y, string, dictionary of font options].
        Default is `None`.
    show : bool, optional
        Whether to show the plot or return the matplotlib object. Default is `True`.


    Returns
    -------
    :class:`matplotlib.plt`
        Matplotlib fig object.
    """
    dpi = 100.0
    figsize = (size[0] / dpi, size[1] / dpi)
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(1, 1, 1)
    if isinstance(plot_data, str):
        plot_data = ast.literal_eval(plot_data)
    for points in plot_data:
        if points[-1] == "fill":
            plt.fill(points[0], points[1], c=points[2], label=points[3], alpha=points[4])
        elif points[-1] == "path":
            path = Path(points[0], points[1])
            patch = PathPatch(path, color=points[2], alpha=points[4], label=points[3])
            ax.add_patch(patch)
        elif points[-1] == "contour":
            path = Path(points[0], points[1])
            patch = PathPatch(path, color=points[2], alpha=points[4], label=points[3], fill=False, linewidth=points[5])
            ax.add_patch(patch)

    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    if show_legend:
        ax.legend(loc="upper right")

    # evaluating the limits
    xmin = ymin = 1e30
    xmax = ymax = -1e30
    for points in plot_data:
        if points[-1] == "fill":
            xmin = min(xmin, min(points[0]))
            xmax = max(xmax, max(points[0]))
            ymin = min(ymin, min(points[1]))
            ymax = max(ymax, max(points[1]))
        else:
            for p in points[0]:
                xmin = min(xmin, p[0])
                xmax = max(xmax, p[0])
                ymin = min(ymin, p[1])
                ymax = max(ymax, p[1])
    if x_limits:
        ax.set_xlim(x_limits)
    else:
        ax.set_xlim([xmin, xmax])
    if y_limits:
        ax.set_ylim(y_limits)
    else:
        ax.set_ylim([ymin, ymax])

    if axis_equal:
        ax.axis("equal")

    if annotations:
        for annotation in annotations:
            plt.text(annotation[0], annotation[1], annotation[2], **annotation[3])

    if snapshot_path:
        plt.savefig(snapshot_path)
    elif show:
        plt.show()
    return plt


@pyaedt_function_handler()
def plot_contour(qty_to_plot, x, y, size=(2000, 1600), xlabel="", ylabel="", title="", levels=64, snapshot_path=None):
    """Create a matplotlib contour plot.

    Parameters
    ----------
    qty_to_plot : :class:`numpy.ndarray`
        Quantity to plot.
    x : :class:`numpy.ndarray`
        X axis quantity.
    y : :class:`numpy.ndarray`
        Y axis quantity.
    size : tuple, list, optional
        Window Size. Default is `(2000,1600)`.
    xlabel : str, optional
        X Label. Default is `""`.
    ylabel : str, optional
        Y Label. Default is `""`.
    title : str, optional
        Plot Title Label. Default is `""`.
    levels : int, optional
        Colormap levels. Default is `64`.
    snapshot_path : str, optional
        Full path to image to save. Default is None.

    Returns
    -------
    :class:`matplotlib.plt`
        Matplotlib fig object.
    """
    dpi = 100.0
    figsize = (size[0] / dpi, size[1] / dpi)
    fig, ax = plt.subplots(figsize=figsize)
    if title:
        plt.title(title)
    if xlabel:
        plt.xlabel(xlabel)
    if ylabel:
        plt.ylabel(ylabel)

    plt.contourf(
        x,
        y,
        qty_to_plot.T,
        levels=levels,
        cmap="jet",
    )

    plt.colorbar()
    if snapshot_path:
        plt.savefig(snapshot_path)
    else:
        plt.show()
    return plt


class ObjClass(object):
    """Manages mesh files to be plotted in pyvista.

    Parameters
    ----------
    path : str
        Full path to the file.
    color : str or tuple
        Can be a string with color name or a tuple with (r,g,b) values.
    opacity : float
        Value between 0 to 1 of opacity.
    units : str
        Model units.

    """

    def __init__(self, path, color, opacity, units):
        self.path = path
        self._color = (0, 0, 0)
        self.color = color
        self.opacity = opacity
        self.units = units
        self._cached_mesh = None
        self._cached_polydata = None
        self.name = os.path.splitext(os.path.basename(self.path))[0]

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, value):
        if isinstance(value, (tuple, list)):
            self._color = value
        elif value in CSS4_COLORS:
            h = CSS4_COLORS[value].lstrip("#")
            self._color = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


class FieldClass(object):
    """Class to manage Field data to be plotted in pyvista.

    Parameters
    ----------
    path : str
        Full path to the file.
    log_scale : bool, optional
        Either if the field has to be plotted log or not. The default value is ``True``.
    coordinate_units : str, optional
        Fields coordinates units. The default value is ``"meter"``.
    opacity : float, optional
        Value between 0 to 1 of opacity. The default value is ``1``.
    color_map : str, optional
        Color map of field plot. The default value is ``"rainbow"``.
    label : str, optional
        Name of the field. The default value is ``"Field"``.
    tolerance : float, optional
        Delauny tolerance value used for interpolating points. The default value is ``1e-3``.
    headers : int, optional
        Number of lines to of the file containing header info that has to be removed.
        The default value is ``2``.
    """

    def __init__(
        self,
        path,
        log_scale=True,
        coordinate_units="meter",
        opacity=1,
        color_map="jet",
        label="Field",
        tolerance=1e-3,
        headers=2,
        show_edge=True,
    ):
        self.path = path
        self.log_scale = log_scale
        self.units = coordinate_units
        self.opacity = opacity
        self.color_map = color_map
        self._cached_mesh = None
        self._cached_polydata = None
        self.label = label
        self.name = os.path.splitext(os.path.basename(self.path))[0]
        self.color = (255, 0, 0)
        self.surface_mapping_tolerance = tolerance
        self.header_lines = headers
        self.show_edge = show_edge
        self._is_frame = False
        self.is_vector = False
        self.vector_scale = 1.0


class CommonPlotter(object):
    def __init__(self):
        self._objects = []
        self._fields = []
        self._frames = []
        self.show_axes = True
        self.show_legend = True
        self.show_grid = True
        self.is_notebook = is_notebook()
        self.gif_file = None
        self._background_color = (255, 255, 255)
        self._background_image = None
        self.off_screen = False
        if self.is_notebook:
            self.windows_size = [600, 600]
        else:
            self.windows_size = [1024, 768]
        self.pv = None
        self._orientation = ["xy", 0, 0, 0]
        self.units = "meter"
        self.frame_per_seconds = 3
        self._plot_meshes = []
        self.range_min = None
        self.range_max = None
        self.image_file = None
        self._camera_position = "yz"
        self._view_up = (0.0, 1.0, 0.0)
        self._focal_point = (0.0, 0.0, 0.0)
        self._roll_angle = 0
        self._azimuth_angle = 0
        self._elevation_angle = 0
        self._zoom = 1
        self._isometric_view = True
        self.bounding_box = True
        self.color_bar = True
        self.array_coordinates = []
        self.meshes = None
        self._x_scale = 1.0
        self._y_scale = 1.0
        self._z_scale = 1.0
        self._convert_fields_in_db = False
        self._log_multiplier = 10.0

    @property
    def convert_fields_in_db(self):
        """Either if convert the fields before plotting in dB. Log scale will be disabled.

        Returns
        -------
        bool
        """
        return self._convert_fields_in_db

    @convert_fields_in_db.setter
    def convert_fields_in_db(self, value):
        self._convert_fields_in_db = value
        for f in self.fields:
            f._cached_polydata = None
        for f in self.frames:
            f._cached_polydata = None

    @property
    def log_multiplier(self):
        """Multiply the log value.

        Returns
        -------
        float
        """
        return self._log_multiplier

    @log_multiplier.setter
    def log_multiplier(self, value):
        self._log_multiplier = value

    @property
    def x_scale(self):
        """Scale plot on X.

        Returns
        -------
        float
        """
        return self._x_scale

    @x_scale.setter
    def x_scale(self, value):
        self._x_scale = value

    @property
    def y_scale(self):
        """Scale plot on Y.

        Returns
        -------
        float
        """
        return self._y_scale

    @y_scale.setter
    def y_scale(self, value):
        self._y_scale = value

    @property
    def z_scale(self):
        """Scale plot on Z.

        Returns
        -------
        float
        """
        return self._z_scale

    @z_scale.setter
    def z_scale(self, value):
        self._z_scale = value

    @property
    def isometric_view(self):
        """Enable or disable the default iso view.

        Parameters
        ----------
        value : bool
            Either if iso view is enabled or disabled.

        Returns
        -------
        bool
        """
        return self._isometric_view

    @isometric_view.setter
    def isometric_view(self, value=True):
        self._isometric_view = value

    @property
    def view_up(self):
        """Get/Set the camera view axis. It disables the default iso view.

        Parameters
        ----------
        value : tuple
            Value of camera view position.

        Returns
        -------
        tuple
        """
        return self._view_up

    @view_up.setter
    def view_up(self, value):
        if isinstance(value, list):
            self._view_up = tuple(value)
        else:
            self._view_up = value
        self.isometric_view = False

    @property
    def focal_point(self):
        """Get/Set the camera focal point value. It disables the default iso view.

        Parameters
        ----------
        value : tuple
            Value of focal point position.

        Returns
        -------
        tuple
        """
        return self._focal_point

    @focal_point.setter
    def focal_point(self, value):
        if isinstance(value, list):
            self._focal_point = tuple(value)
        else:
            self._focal_point = value
        self.isometric_view = False

    @property
    def camera_position(self):
        """Get or set the camera position value. This parameter disables the default iso view.
        Value for the camera position. The value is for ``"xy"``, ``"xz"`` or ``"yz"``.

        Returns
        -------
        str
        """
        return self._camera_position

    @camera_position.setter
    def camera_position(self, value):
        if isinstance(value, list):
            self._camera_position = tuple(value)
        else:
            self._camera_position = value
        self.isometric_view = False

    @property
    def roll_angle(self):
        """Get/Set the roll angle value. It disables the default iso view.

        Parameters
        ----------
        value : float
            Value of roll angle in degrees.

        Returns
        -------
        float
        """
        return self._roll_angle

    @roll_angle.setter
    def roll_angle(self, value=20):
        self._roll_angle = value
        self.isometric_view = False

    @property
    def azimuth_angle(self):
        """Get/Set the azimuth angle value. It disables the default iso view.

        Parameters
        ----------
        value : float
            Value of azimuth angle in degrees.

        Returns
        -------
        float
        """
        return self._azimuth_angle

    @azimuth_angle.setter
    def azimuth_angle(self, value=45):
        self._azimuth_angle = value
        self.use_default_iso_view = False

    @property
    def elevation_angle(self):
        """Get/Set the elevation angle value. It disables the default iso view.

        Parameters
        ----------
        value : float
            Value of elevation angle in degrees.

        Returns
        -------
        float
        """
        return self._elevation_angle

    @elevation_angle.setter
    def elevation_angle(self, value=45):
        self._elevation_angle = value
        self.use_default_iso_view = False

    @property
    def zoom(self):
        """Get/Set the zoom value.

        Parameters
        ----------
        value : float
            Value of zoom in degrees.

        Returns
        -------
        float
        """
        return self._zoom

    @zoom.setter
    def zoom(self, value=1):
        self._zoom = value

    @pyaedt_function_handler()
    def set_orientation(self, camera_position="xy", roll_angle=0, azimuth_angle=45, elevation_angle=20):
        """Change the plot default orientation.

        Parameters
        ----------
        camera_position : str
            Camera view. Default is `"xy"`. Options are `"xz"` and `"yz"`.
        roll_angle : int, float
            Roll camera angle on the specified the camera_position.
        azimuth_angle : int, float
            Azimuth angle of camera on the specified the camera_position.
        elevation_angle : int, float
            Elevation camera angle on the specified the camera_position.

        Returns
        -------
        bool
        """
        if camera_position in ["xy", "yz", "xz"]:
            self.camera_position = camera_position
        else:
            warnings.warn("Plane has to be one of xy, xz, yz.")
        self.roll_angle = roll_angle
        self.azimuth_angle = azimuth_angle
        self.elevation_angle = elevation_angle
        self.use_default_iso_view = False
        return True

    @property
    def background_color(self):
        """Background color.
        It can be a tuple of (r,g,b)  or color name.
        """
        return self._background_color

    @background_color.setter
    def background_color(self, value):
        if isinstance(value, (tuple, list)):
            self._background_color = value
        elif value in CSS4_COLORS:
            h = CSS4_COLORS[value].lstrip("#")
            self._background_color = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

    @property
    def background_image(self):
        """Background image.

        Returns
        -------
        str
        """
        return self._background_image

    @background_image.setter
    def background_image(self, value):
        if os.path.exists(value):
            self._background_image = value


class ModelPlotter(CommonPlotter):
    """Manages the data to be plotted with ``pyvista``.

    Examples
    --------
    This Class can be instantiated within Pyaedt (with plot_model_object or different field plots
    and standalone).
    Here an example of standalone project

    >>> model = ModelPlotter()
    >>> model.add_object(r'D:\Simulation\antenna.obj', (200,20,255), 0.6, "in")
    >>> model.add_object(r'D:\Simulation\helix.obj', (0,255,0), 0.5, "in")
    >>> model.add_field_from_file(r'D:\Simulation\helic_antenna.csv', True, "meter", 1)
    >>> model.background_color = (0,0,0)
    >>> model.plot()

    And here an example of animation:

    >>> model = ModelPlotter()
    >>> model.add_object(r'D:\Simulation\antenna.obj', (200,20,255), 0.6, "in")
    >>> model.add_object(r'D:\Simulation\helix.obj', (0,255,0), 0.5, "in")
    >>> frames = [r'D:\Simulation\helic_antenna.csv', r'D:\Simulation\helic_antenna_10.fld',
    ...           r'D:\Simulation\helic_antenna_20.fld', r'D:\Simulation\helic_antenna_30.fld',
    ...           r'D:\Simulation\helic_antenna_40.fld']
    >>> model.gif_file = r"D:\Simulation\animation.gif"
    >>> model.animate()
    """

    def __init__(self):
        CommonPlotter.__init__(self)

    @property
    def fields(self):
        """List of fields object.

        Returns
        -------
        list of :class:`pyaedt.modules.AdvancedPostProcessing.FieldClass`
        """
        return self._fields

    @property
    def frames(self):
        """Frames list for animation.

        Returns
        -------
        list of :class:`pyaedt.modules.AdvancedPostProcessing.FieldClass`
        """
        return self._frames

    @property
    def objects(self):
        """List of class objects.

        Returns
        -------
        list of :class:`pyaedt.modules.AdvancedPostProcessing.ObjClass`
        """
        return self._objects

    @pyaedt_function_handler()
    def add_object(self, cad_path, cad_color="dodgerblue", opacity=1, units="mm"):
        """Add an mesh file to the scenario. It can be obj or any of pyvista supported files.

        Parameters
        ----------
        cad_path : str
            Full path to the file.
        cad_color : str or tuple
            Can be a string with color name or a tuple with (r,g,b) values.
            The default value is ``"dodgerblue"``.
        opacity : float
            Value between 0 to 1 of opacity. The default value is ``1``.
        units : str
            Model units. The default value is ``"mm"``.

        Returns
        -------
        bool
        """
        self._objects.append(ObjClass(cad_path, cad_color, opacity, units))
        self.units = units
        return True

    @pyaedt_function_handler()
    def add_field_from_file(
        self,
        field_path,
        log_scale=True,
        coordinate_units="meter",
        opacity=1,
        color_map="jet",
        label_name="Field",
        surface_mapping_tolerance=1e-3,
        header_lines=2,
        show_edges=True,
    ):
        """Add a field file to the scenario.
        It can be aedtplt, fld or csv file or any txt file with 4 column [x,y,z,field].
        If text file they have to be space separated column.

        Parameters
        ----------
        field_path : str
            Full path to the file.
        log_scale : bool
            Either if the field has to be plotted log or not.
        coordinate_units : str
            Fields coordinates units.
        opacity : float
            Value between 0 to 1 of opacity.
        color_map : str
            Color map of field plot. Default rainbow.
        label_name : str, optional
            Name of the field.
        surface_mapping_tolerance : float, optional
            Delauny tolerance value used for interpolating points.
        header_lines : int
            Number of lines to of the file containing header info that has to be removed.

        Returns
        -------
        bool
        """
        self._fields.append(
            FieldClass(
                field_path,
                log_scale,
                coordinate_units,
                opacity,
                color_map,
                label_name,
                surface_mapping_tolerance,
                header_lines,
                show_edges,
            )
        )

    @pyaedt_function_handler()
    def add_frames_from_file(
        self,
        field_files,
        log_scale=True,
        coordinate_units="meter",
        opacity=1,
        color_map="jet",
        label_name="Field",
        surface_mapping_tolerance=1e-3,
        header_lines=2,
    ):
        """Add a field file to the scenario. It can be aedtplt, fld or csv file.

        Parameters
        ----------
        field_files : list
            List of full path to frame file.
        log_scale : bool
            Either if the field has to be plotted log or not.
        coordinate_units : str
            Fields coordinates units.
        opacity : float
            Value between 0 to 1 of opacity.
        color_map : str
            Color map of field plot. Default rainbow.
        label_name : str, optional
            Name of the field.
        surface_mapping_tolerance : float, optional
            Delauny tolerance value used for interpolating points.
        header_lines : int
            Number of lines to of the file containing header info that has to be removed.

        Returns
        -------
        bool
        """
        for field in field_files:
            self._frames.append(
                FieldClass(
                    field,
                    log_scale,
                    coordinate_units,
                    opacity,
                    color_map,
                    label_name,
                    surface_mapping_tolerance,
                    header_lines,
                    False,
                )
            )
            self._frames[-1]._is_frame = True

    @pyaedt_function_handler()
    def add_field_from_data(
        self,
        coordinates,
        fields_data,
        log_scale=True,
        coordinate_units="meter",
        opacity=1,
        color_map="jet",
        label_name="Field",
        surface_mapping_tolerance=1e-3,
        show_edges=True,
    ):
        """Add field data to the scenario.

        Parameters
        ----------
        coordinates : list of list
            List of list [x,y,z] coordinates.
        fields_data : list
            List of list Fields Value.
        log_scale : bool
            Either if the field has to be plotted log or not.
        coordinate_units : str
            Fields coordinates units.
        opacity : float
            Value between 0 to 1 of opacity.
        color_map : str
            Color map of field plot. Default rainbow.
        label_name : str, optional
            Name of the field.
        surface_mapping_tolerance : float, optional
            Delauny tolerance value used for interpolating points.

        Returns
        -------
        bool
        """
        self._fields.append(
            FieldClass(
                None, log_scale, coordinate_units, opacity, color_map, label_name, surface_mapping_tolerance, show_edges
            )
        )
        vertices = np.array(coordinates)
        filedata = pv.PolyData(vertices)
        filedata = filedata.delaunay_2d(tol=surface_mapping_tolerance)
        filedata.point_data[self.fields[-1].label] = np.array(fields_data)
        self.fields[-1]._cached_polydata = filedata

    @pyaedt_function_handler()
    def _read_mesh_files(self, read_frames=False):
        for cad in self.objects:
            if not cad._cached_polydata:
                filedata = pv.read(cad.path)
                cad._cached_polydata = filedata
            color_cad = [i / 255 for i in cad.color]
            cad._cached_mesh = self.pv.add_mesh(cad._cached_polydata, color=color_cad, opacity=cad.opacity)
            if self.meshes:
                self.meshes += cad._cached_polydata
            else:
                self.meshes = cad._cached_polydata
        obj_to_iterate = [i for i in self._fields]
        if read_frames:
            for i in self.frames:
                obj_to_iterate.append(i)
        for field in obj_to_iterate:
            if field.path and not field._cached_polydata:
                if ".case" in field.path:
                    reader = pv.get_reader(os.path.abspath(field.path)).read()
                    field._cached_polydata = reader[reader.keys()[0]].extract_surface()
                    field.label = field._cached_polydata.point_data.active_scalars_name

                elif ".aedtplt" in field.path:
                    vertices, faces, scalars, log1 = _parse_aedtplt(field.path)
                    if self.convert_fields_in_db:
                        scalars = [np.multiply(np.log10(i), self.log_multiplier) for i in scalars]
                    fields_vals = pv.PolyData(vertices[0], faces[0])
                    field._cached_polydata = fields_vals
                    if isinstance(scalars[0], list):
                        vector_scale = (max(fields_vals.bounds) - min(fields_vals.bounds)) / (
                            50 * (np.vstack(scalars[0]).max() - np.vstack(scalars[0]).min())
                        )

                        field._cached_polydata["vectors"] = np.vstack(scalars[0]).T * vector_scale
                        field.label = "Vector " + field.label
                        field._cached_polydata.point_data[field.label] = np.array(
                            [np.linalg.norm(x) for x in np.vstack(scalars[0]).T]
                        )

                        field.is_vector = True
                    else:
                        field._cached_polydata.point_data[field.label] = scalars[0]
                        field.is_vector = False
                    field.log = log1
                else:
                    nodes = []
                    values = []
                    is_vector = False
                    with open_file(field.path, "r") as f:
                        try:
                            lines = f.read().splitlines()[field.header_lines :]
                            if ".csv" in field.path:
                                sniffer = csv.Sniffer()
                                delimiter = sniffer.sniff(lines[0]).delimiter
                            else:
                                delimiter = " "
                            if len(lines) > 2000 and not field._is_frame:
                                lines = list(dict.fromkeys(lines))
                                # decimate = 2
                                # del lines[decimate - 1 :: decimate]
                        except:
                            lines = []
                        for line in lines:
                            tmp = line.strip().split(delimiter)
                            if len(tmp) < 4:
                                continue
                            nodes.append([float(tmp[0]), float(tmp[1]), float(tmp[2])])
                            if len(tmp) == 6:
                                values.append([float(tmp[3]), float(tmp[4]), float(tmp[5])])
                                is_vector = True
                            elif len(tmp) == 9:
                                values.append([float(tmp[3]), float(tmp[5]), float(tmp[7])])
                                is_vector = True
                            else:
                                values.append(float(tmp[3]))
                    if self.convert_fields_in_db:
                        if not isinstance(values[0], list):
                            values = [self.log_multiplier * math.log10(abs(i)) for i in values]
                        else:
                            values = [[self.log_multiplier * math.log10(abs(i)) for i in value] for value in values]
                    if nodes:
                        try:
                            conv = 1 / AEDT_UNITS["Length"][self.units]
                        except:
                            conv = 1
                        vertices = np.array(nodes) * conv
                        filedata = pv.PolyData(vertices)
                        if is_vector:
                            vector_scale = (max(filedata.bounds) - min(filedata.bounds)) / (
                                20 * (np.vstack(values).max() - np.vstack(values).min())
                            )
                            filedata["vectors"] = np.vstack(values) * vector_scale
                            field.label = "Vector " + field.label
                            filedata.point_data[field.label] = np.array([np.linalg.norm(x) for x in np.vstack(values)])
                            field.is_vector = True
                        else:
                            filedata = filedata.delaunay_2d(tol=field.surface_mapping_tolerance)
                            filedata.point_data[field.label] = np.array(values)
                        field._cached_polydata = filedata

    @pyaedt_function_handler()
    def _add_buttons(self):
        size = int(self.pv.window_size[1] / 40)
        startpos = self.pv.window_size[1] - 2 * size
        endpos = 100
        color = self.pv.background_color
        axes_color = [0 if i >= 0.5 else 255 for i in color]
        buttons = []
        texts = []
        max_elements = (startpos - endpos) // (size + (size // 10))

        class SetVisibilityCallback:
            """Helper callback to keep a reference to the actor being modified."""

            def __init__(self, actor):
                self.actor = actor

            def __call__(self, state):
                try:
                    self.actor._cached_mesh.SetVisibility(state)
                except AttributeError:
                    self.actor.SetVisibility(state)

        class ChangePageCallback:
            """Helper callback to keep a reference to the actor being modified."""

            def __init__(self, plot, actor, axes_color):
                self.plot = plot
                self.actors = actor
                self.id = 0
                self.endpos = 100
                self.size = int(plot.window_size[1] / 40)
                self.startpos = plot.window_size[1] - 2 * self.size
                self.max_elements = (self.startpos - self.endpos) // (self.size + (self.size // 10))
                self.i = self.max_elements
                self.axes_color = axes_color
                self.text = []

            def __call__(self, state):
                try:
                    self.plot.button_widgets = [self.plot.button_widgets[0]]
                except:
                    self.plot.button_widgets = []
                self.id += 1
                k = 0
                startpos = self.startpos
                while k < self.max_elements:
                    if len(self.text) > k:
                        self.plot.remove_actor(self.text[k])
                    k += 1
                self.text = []
                k = 0

                while k < min(self.max_elements, len(self.actors)):
                    if self.i >= len(self.actors):
                        self.i = 0
                        self.id = 0
                    callback = SetVisibilityCallback(self.actors[self.i])
                    self.plot.add_checkbox_button_widget(
                        callback,
                        value=self.actors[self.i]._cached_mesh.GetVisibility() == 1,
                        position=(5.0, startpos),
                        size=self.size,
                        border_size=1,
                        color_on=[i / 255 for i in self.actors[self.i].color],
                        color_off="grey",
                        background_color=None,
                    )
                    self.text.append(
                        self.plot.add_text(
                            self.actors[self.i].name,
                            position=(25.0, startpos),
                            font_size=self.size // 3,
                            color=self.axes_color,
                        )
                    )
                    startpos = startpos - self.size - (self.size // 10)
                    k += 1
                    self.i += 1

        if len(self.objects) > 100:
            actors = [i for i in self._fields if i._cached_mesh] + self._objects
        else:
            actors = [i for i in self._fields if i._cached_mesh] + self._objects
        # if texts and len(texts) < len(actors):
        callback = ChangePageCallback(self.pv, actors, axes_color)

        callback.__call__(False)
        if callback.max_elements < len(actors):
            self.pv.add_checkbox_button_widget(
                callback,
                value=True,
                position=(5.0, self.pv.window_size[1]),
                size=int(1.5 * size),
                border_size=2,
                color_on=axes_color,
                color_off=axes_color,
            )
            self.pv.add_text("Next", position=(50.0, self.pv.window_size[1]), font_size=size // 3, color="grey")
            self.pv.button_widgets.insert(
                0, self.pv.button_widgets.pop(self.pv.button_widgets.index(self.pv.button_widgets[-1]))
            )

    @pyaedt_function_handler()
    def plot(self, export_image_path=None):
        """Plot the current available Data. With `s` key a screenshot is saved in export_image_path or in tempdir.

        Parameters
        ----------
        export_image_path : str
            Path to image to save.

        Returns
        -------
        bool
        """
        self.pv = pv.Plotter(notebook=self.is_notebook, off_screen=self.off_screen, window_size=self.windows_size)
        self.pv.enable_ssao()
        self.meshes = None
        if self.background_image:
            self.pv.add_background_image(self.background_image)
        else:
            self.pv.background_color = [i / 255 for i in self.background_color]
        self._read_mesh_files()
        axes_color = [0 if i >= 128 else 255 for i in self.background_color]
        if self.color_bar:
            sargs = dict(
                title_font_size=10,
                label_font_size=10,
                shadow=True,
                n_labels=9,
                italic=True,
                fmt="%.1f",
                font_family="arial",
                interactive=True,
                color=axes_color,
                vertical=False,
            )
        else:
            sargs = dict(
                position_x=2,
                position_y=2,
            )
        for field in self._fields:
            if field.is_vector:
                field._cached_polydata.set_active_vectors("vectors")
                field._cached_polydata["vectors"] = field._cached_polydata["vectors"] * field.vector_scale
                self.pv.add_mesh(
                    field._cached_polydata.arrows,
                    scalars=field.label,
                    log_scale=False if self.convert_fields_in_db else field.log_scale,
                    scalar_bar_args=sargs,
                    cmap=field.color_map,
                )
                field._cached_polydata["vectors"] = field._cached_polydata["vectors"] / field.vector_scale
            elif self.range_max is not None and self.range_min is not None:
                field._cached_mesh = self.pv.add_mesh(
                    field._cached_polydata,
                    scalars=field.label,
                    log_scale=False if self.convert_fields_in_db else field.log_scale,
                    scalar_bar_args=sargs,
                    cmap=field.color_map,
                    clim=[self.range_min, self.range_max],
                    opacity=field.opacity,
                    show_edges=field.show_edge,
                )
            else:
                field._cached_mesh = self.pv.add_mesh(
                    field._cached_polydata,
                    scalars=field.label,
                    log_scale=False if self.convert_fields_in_db else field.log_scale,
                    scalar_bar_args=sargs,
                    cmap=field.color_map,
                    opacity=field.opacity,
                    show_edges=field.show_edge,
                    smooth_shading=True,
                    split_sharp_edges=True,
                )

        self.pv.set_scale(self.x_scale, self.y_scale, self.z_scale)

        if self.show_legend:
            self._add_buttons()

        if self.show_axes:
            self.pv.show_axes()
        if not self.is_notebook and self.show_grid:
            self.pv.show_grid(color=tuple(axes_color), grid=self.show_grid, fmt="%.2e")
        if self.bounding_box:
            self.pv.add_bounding_box(color=tuple(axes_color))

        if not self.isometric_view:
            self.pv.set_focus(self.pv.mesh.center)
            if isinstance(self.camera_position, (tuple, list)):
                self.pv.camera.position = self.camera_position
                self.pv.camera.focal_point = self.focal_point
                self.pv.camera.viewup = self.view_up
            else:
                self.pv.camera_position = self.camera_position
                self.pv.camera.focal_point = self.focal_point
            self.pv.camera.azimuth += self.azimuth_angle
            self.pv.camera.roll += self.roll_angle
            self.pv.camera.elevation += self.elevation_angle
        else:
            self.pv.isometric_view()
        self.pv.camera.zoom(self.zoom)
        if export_image_path:
            path_image = os.path.dirname(export_image_path)
            root_name, format = os.path.splitext(os.path.basename(export_image_path))
        else:
            path_image = tempfile.gettempdir()  # pragma: no cover
            format = ".png"  # pragma: no cover
            root_name = "Image"  # pragma: no cover

        def s_callback():  # pragma: no cover
            """Save screenshots"""
            exp = os.path.join(
                path_image, "{}{}{}".format(root_name, datetime.now().strftime("%Y_%M_%d_%H-%M-%S"), format)
            )
            self.pv.screenshot(exp, return_img=False)

        self.pv.add_key_event("s", s_callback)
        if export_image_path:
            self.pv.show(screenshot=export_image_path, full_screen=True)
        elif self.is_notebook:  # pragma: no cover
            self.pv.show()  # pragma: no cover
        else:
            self.pv.show(full_screen=True)  # pragma: no cover

        self.image_file = export_image_path
        return True

    @pyaedt_function_handler()
    def clean_cache_and_files(self, remove_objs=True, remove_fields=True, clean_cache=False):
        """Clean downloaded files, and, on demand, also the cached meshes.

        Parameters
        ----------
        remove_objs : bool
        remove_fields : bool
        clean_cache : bool

        Returns
        -------
        bool
        """
        if remove_objs:
            for el in self.objects:
                if os.path.exists(el.path):
                    os.remove(el.path)
                if clean_cache:
                    el._cached_mesh = None
                    el._cached_polydata = None
        if remove_fields:
            for el in self.fields:
                if os.path.exists(el.path):
                    os.remove(el.path)
                if clean_cache:
                    el._cached_mesh = None
                    el._cached_polydata = None
        return True

    @pyaedt_function_handler()
    def animate(self):
        """Animate the current field plot.

        Returns
        -------
        bool
        """
        assert len(self.frames) > 0, "Number of Fields have to be greater than 1 to do an animation."
        if self.is_notebook:
            self.pv = pv.Plotter(notebook=self.is_notebook, off_screen=True, window_size=self.windows_size)
        else:
            self.pv = pv.Plotter(notebook=self.is_notebook, off_screen=self.off_screen, window_size=self.windows_size)
        if self.background_image:
            self.pv.add_background_image(self.background_image)
        else:
            self.pv.background_color = [i / 255 for i in self.background_color]
        self._read_mesh_files(read_frames=True)

        axes_color = [0 if i >= 128 else 1 for i in self.background_color]

        self.pv.set_scale(self.x_scale, self.y_scale, self.z_scale)
        if self.show_axes:
            self.pv.show_axes()
        if self.show_grid and not self.is_notebook:
            self.pv.show_grid(color=tuple(axes_color))
        if self.bounding_box:
            self.pv.add_bounding_box(color=tuple(axes_color))
        if self.show_legend:
            labels = []
            for m in self.objects:
                labels.append([m.name, [i / 255 for i in m.color]])
            for m in self.fields:
                labels.append([m.name, "red"])
            self.pv.add_legend(labels=labels, bcolor=None, face="circle", size=[0.15, 0.15])

        self._animating = True

        if self.gif_file:
            self.pv.open_gif(self.gif_file)

        def q_callback():
            """Exit when user wants to leave"""
            self._animating = False

        self._pause = False

        def p_callback():
            """Exit when user wants to leave"""
            self._pause = not self._pause

        self.pv.add_text(
            "Press p for Play/Pause, Press q to exit ", font_size=8, position="upper_left", color=tuple(axes_color)
        )
        self.pv.add_text(" ", font_size=10, position=[0, 0], color=tuple(axes_color))
        self.pv.add_key_event("q", q_callback)
        self.pv.add_key_event("p", p_callback)
        if self.color_bar:
            sargs = dict(
                title_font_size=10,
                label_font_size=10,
                shadow=True,
                n_labels=9,
                italic=True,
                fmt="%.1f",
                font_family="arial",
            )
        else:
            sargs = dict(
                position_x=2,
                position_y=2,
            )

        for field in self._fields:
            field._cached_mesh = self.pv.add_mesh(
                field._cached_polydata,
                scalars=field.label,
                log_scale=False if self.convert_fields_in_db else field.log_scale,
                scalar_bar_args=sargs,
                cmap=field.color_map,
                opacity=field.opacity,
            )

        if self.range_min is not None and self.range_max is not None:
            mins = self.range_min
            maxs = self.range_max
        else:
            mins = 1e20
            maxs = -1e20
            for el in self.frames:
                if np.min(el._cached_polydata.point_data[el.label]) < mins:
                    mins = np.min(el._cached_polydata.point_data[el.label])
                if np.max(el._cached_polydata.point_data[el.label]) > maxs:
                    maxs = np.max(el._cached_polydata.point_data[el.label])

        self.frames[0]._cached_mesh = self.pv.add_mesh(
            self.frames[0]._cached_polydata,
            scalars=self.frames[0].label,
            log_scale=False if self.convert_fields_in_db else self.frames[0].log_scale,
            scalar_bar_args=sargs,
            cmap=self.frames[0].color_map,
            clim=[mins, maxs],
            show_edges=False,
            pickable=True,
            smooth_shading=True,
            name="FieldPlot",
            opacity=self.frames[0].opacity,
        )
        # run until q is pressed
        if self.pv.mesh:
            self.pv.set_focus(self.pv.mesh.center)
        if not self.isometric_view:
            if isinstance(self.camera_position, (tuple, list)):
                self.pv.camera.position = self.camera_position
                self.pv.camera.focal_point = self.focal_point
                self.pv.camera.up = self.view_up
            else:
                self.pv.camera_position = self.camera_position
            self.pv.camera.azimuth += self.azimuth_angle
            self.pv.camera.roll += self.roll_angle
            self.pv.camera.elevation += self.elevation_angle
        else:
            self.pv.isometric_view()
        self.pv.camera.zoom(self.zoom)
        cpos = self.pv.show(interactive=False, auto_close=False, interactive_update=not self.off_screen)

        start = time.time()
        try:
            self.pv.update(1, force_redraw=True)
        except:
            pass
        if self.gif_file:
            first_loop = True
            self.pv.write_frame()
        else:
            first_loop = False
        i = 1
        while self._animating:
            if self._pause:
                time.sleep(1)
                self.pv.update(1, force_redraw=True)
                continue
            # p.remove_actor("FieldPlot")
            if i >= len(self.frames):
                if self.off_screen or self.is_notebook:
                    break
                i = 0
                first_loop = False
            scalars = self.frames[i]._cached_polydata.point_data[self.frames[i].label]
            self.pv.update_scalars(scalars, render=False)
            if not hasattr(self.pv, "ren_win"):
                break
            time.sleep(max(0, (1 / self.frame_per_seconds) - (time.time() - start)))
            start = time.time()
            if self.off_screen:
                self.pv.render()
            else:
                self.pv.update(1, force_redraw=True)
            if first_loop:
                self.pv.write_frame()
            i += 1
        self.pv.close()
        if self.gif_file:
            return self.gif_file
        else:
            return True

    @pyaedt_function_handler()
    def generate_geometry_mesh(self):
        """Generate mesh for objects only.

        Returns
        -------
        Mesh
        """
        self.pv = pv.Plotter(notebook=self.is_notebook, off_screen=self.off_screen, window_size=self.windows_size)
        self._read_mesh_files()
        if self.array_coordinates:
            duplicate_mesh = self.meshes.copy()
            for offset_xyz in self.array_coordinates:
                translated_mesh = duplicate_mesh.copy()
                translated_mesh.translate(offset_xyz, inplace=True)
                self.meshes += translated_mesh
        return self.meshes
