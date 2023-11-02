from collections import defaultdict
import math
import os
import warnings

import numpy as np
import pyvista as pv

from pyaedt import pyaedt_function_handler
from pyaedt.generic.constants import AEDT_UNITS
from pyaedt.generic.plot import CommonPlotter, ObjClass


class HDMPlotter(CommonPlotter):
    """Manages Hdm data to be plotted with ``pyvista``.

    Note: the methods in this class are just examples and subject
    to improvement and changes.
    """

    def __init__(self):
        CommonPlotter.__init__(self)
        self._bundle = None
        self.show_as_standalone = True
        self.units = "meter"

    @property
    def hdm_data(self):
        """Return the ``hds`` Data parsed."""
        return self._bundle

    @pyaedt_function_handler()
    def add_cad_model(self, filename, cad_color="dodgerblue", opacity=1, units="mm"):
        """Add a ``stl`` file to the scenario.

        Parameters
        ----------
        filename : str
            Full path to stl file.

        Returns
        -------
        bool
            ``True`` if imported.
        """
        if os.path.exists(filename):
            self._objects.append(ObjClass(filename, cad_color, opacity, units=units))
            self.units = units
            return True
        return False

    @pyaedt_function_handler()
    def add_hdm_bundle_from_file(self, filename, units=None):
        from pyaedt.sbrplus.hdm_parser import Parser

        if os.path.exists(filename):
            self._bundle = Parser(filename=filename).parse_message()
            self._bundle_units = units

    @pyaedt_function_handler()
    def _add_rays(self):
        from itertools import chain

        if not self._bundle:
            return False
        points = []
        lines = []  # data structure for PyVista
        depths = []  # track depth at each point in the track segments

        def add_ray_segment(depth, bounce):
            def add_ray_helper(depth, next_bounce):
                lines.append([len(points) + i for i in range(2)])
                depths.extend([depth, depth])
                points.extend([bounce.hit_pt, next_bounce.hit_pt])
                add_ray_segment(depth + 1, next_bounce)

            # add more segments to the ray track rendering data
            if bounce.refl_bounce:
                add_ray_helper(depth, bounce.refl_bounce)
            if bounce.trans_bounce:
                add_ray_helper(depth, bounce.trans_bounce)

        for track in self._bundle.ray_tracks:
            if track.track_type == "UTD":
                new_track_seg = [track.source_point, track.utd_point, track.first_bounce.hit_pt]
            else:
                new_track_seg = [track.source_point, track.first_bounce.hit_pt]
            lines.append([len(points) + i for i in range(len(new_track_seg))])
            depths.extend([1 for i in range(len(new_track_seg))])
            points.extend(new_track_seg)
            add_ray_segment(2, track.first_bounce)

        lines = [[len(l), *l] for l in lines]
        lines = [len(lines), *(chain.from_iterable(lines))]
        return points, lines, depths

    @pyaedt_function_handler()
    def plot_rays(self, snapshot_path=None):
        """Plot Rays read from an ``hdm`` file.

        Parameters
        ----------
        snapshot_path : str, optional
            Full path to exported image file. If ``None`` the plot will be shown.

        Returns
        -------
        :class:`pyvista.Plotter`


        Notes
        -----
        This method is intended to be an example of the usage that can be made of hdm file.

        """
        warnings.warn("This method is intended to be an example of the usage that can be made of hdm file.")
        if snapshot_path:
            self.pv = pv.Plotter(notebook=self.is_notebook, off_screen=True, window_size=self.windows_size)
        else:
            self.pv = pv.Plotter(notebook=self.is_notebook, off_screen=self.off_screen, window_size=self.windows_size)

        self._add_objects()
        points, lines, depths = self._add_rays()
        try:
            conv = 1 / AEDT_UNITS["Length"][self.units]
        except:
            conv = 1
        points = [i * conv for i in points]
        depth1 = pv.PolyData(points, lines=lines)
        annotations = {i: str(i) for i in range(1, 7)}
        self.pv.add_mesh(
            depth1,
            scalars=depths,
            annotations=annotations,
            clim=[0.5, 6.5],
            cmap=["green", "blue", "yellow", "red", "purple", "cyan"],
            categories=True,
            scalar_bar_args={"n_colors": 256, "n_labels": 0, "title": "Depth"},
        )
        if snapshot_path:
            self.pv.show(screenshot=snapshot_path, full_screen=True)
        else:
            self.pv.show()
        return self.pv

    @pyaedt_function_handler()
    def _first_bounce_currents(self):
        bounces = defaultdict(lambda: np.ndarray(3, np.complex128))
        for track in self._bundle.ray_tracks:
            bounce = track.first_bounce
            totalH = bounce.h_inc + bounce.h_refl
            if bounce.h_trans:
                totalH += bounce.h_trans
            offset = 0.01 * bounce.surf_norm
            bounceHash = tuple((i + offset).tobytes() for i in bounce.footprint_vertices)
            bounces[bounceHash] += totalH
        return bounces

    @pyaedt_function_handler()
    def plot_first_bounce_currents(self, snapshot_path=None):
        """Plot First bounce of currents read from an ``hdm`` file.

        Parameters
        ----------
        snapshot_path : str, optional
            Full path to exported image file. If ``None`` the plot will be shown.

        Returns
        -------
        :class:`pyvista.Plotter`
        """
        warnings.warn("This method is intended to be an example of the usage that can be made of hdm file.")
        currents = self._first_bounce_currents()
        points = []
        faces = []
        colors = []
        for f, value in currents.items():
            faces.extend([3, *(len(points) + i for i in range(3))])
            for _ in range(3):
                points.extend([np.frombuffer(thisfpt) for thisfpt in f])

            colors.append(10 * math.log10(np.linalg.norm(value)))
        if snapshot_path:
            self.pv = pv.Plotter(notebook=self.is_notebook, off_screen=True, window_size=self.windows_size)
        else:
            self.pv = pv.Plotter(notebook=self.is_notebook, off_screen=self.off_screen, window_size=self.windows_size)

        self._add_objects()
        try:
            conv = 1 / AEDT_UNITS["Length"][self.units]
        except:
            conv = 1
        points = [i * conv for i in points]
        fb = pv.PolyData(points, faces=faces)
        self.pv.add_mesh(fb, scalars=colors)
        if snapshot_path:
            self.pv.show(screenshot=snapshot_path, full_screen=True)
        else:
            self.pv.show()

    @pyaedt_function_handler()
    def _add_objects(self):
        if self._objects:
            for cad in self._objects:
                if not cad._cached_polydata:
                    filedata = pv.read(cad.path)
                    cad._cached_polydata = filedata
                color_cad = [i / 255 for i in cad.color]
                cad._cached_mesh = self.pv.add_mesh(cad._cached_polydata, color=color_cad, opacity=cad.opacity)
