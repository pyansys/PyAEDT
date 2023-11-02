import os
import warnings

from pyaedt.generic.general_methods import is_ironpython, pyaedt_function_handler, settings

logger = settings.logger
if not is_ironpython:
    try:
        import numpy as np

    except ImportError:
        warnings.warn("numpy package is needed")

    try:
        import pyvista as pv
        import vtk
    except ImportError:
        warnings.warn("pyvista package is needed")

    try:
        import osmnx as ox
        import srtm
        import utm

    except ImportError:
        warnings.warn("OpenStreetMap Reader requires utm, osmnx and srtm extra packages")


class BuildingsPrep(object):
    """Contains all basic functions needed to generate buildings stl files."""

    def __init__(self, cad_path):
        self.cad_path = cad_path

    @staticmethod
    @pyaedt_function_handler()
    def create_building_roof(all_pos):
        """Generate a filled in polygon from outline.
        Includes concave and convex shapes.

        Parameters
        ----------
        all_pos : list

        Returns
        -------
        :class:`pyvista.PolygonData`
        """
        points = vtk.vtkPoints()
        for each in all_pos:
            points.InsertNextPoint(each[0], each[1], each[2])

        # Create the polygon
        polygon = vtk.vtkPolygon()
        polygon.GetPointIds().SetNumberOfIds(len(all_pos))  # make a quad
        for n in range(len(all_pos)):
            polygon.GetPointIds().SetId(n, n)

        # Add the polygon to a list of polygons
        polygons = vtk.vtkCellArray()
        polygons.InsertNextCell(polygon)

        # Create a PolyData
        polygonPolyData = vtk.vtkPolyData()
        polygonPolyData.SetPoints(points)
        polygonPolyData.SetPolys(polygons)

        # Create a mapper and actor
        mapper = vtk.vtkPolyDataMapper()

        mapper.SetInputData(polygonPolyData)

        triFilter = vtk.vtkTriangleFilter()
        # let's filter the polydata
        triFilter.SetInputData(polygonPolyData)
        triFilter.Update()

        polygonPolyDataFiltered = triFilter.GetOutput()
        roof = pv.PolyData(polygonPolyDataFiltered)
        return roof

    @pyaedt_function_handler()
    def generate_buildings(self, center_lat_lon, terrain_mesh, max_radius=500):
        """Generate the buildings stl file.

        Parameters
        ----------
        center_lat_lon : list
            Latitude and longitude.
        terrain_mesh : :class:`pyvista.PolygonData`
            Terrain mesh.
        max_radius : float, int
            Radius around latitude and longitude.

        Returns
        -------
        dict
            Info of generated stl file.
        """
        gdf = ox.geometries.geometries_from_point(center_lat_lon, tags={"building": True}, dist=max_radius)
        utm_center = utm.from_latlon(center_lat_lon[0], center_lat_lon[1])
        center_offset_x = utm_center[0]
        center_offset_y = utm_center[1]

        if len(gdf) == 0:
            logger.info("No Buildings Exists in Selected Geometry")
            return {"file_name": None, "mesh": None}
        else:
            gdf_proj = ox.project_gdf(gdf)

            geo = gdf_proj["geometry"]
            try:
                levels = gdf_proj["building:levels"]
                levels = levels.array
            except KeyError:
                levels = [1] * len(geo)
            try:
                height = gdf_proj["height"]
                height = height.array
            except KeyError:
                height = [10] * len(geo)

            temp = [levels, height]
            geo = geo.array

            building_meshes = pv.PolyData()  # empty location where all building meshses are stored

            logger.info("\nGenerating Buildings")
            last_displayed = -1
            for n, _ in enumerate(geo):
                g = geo[n]
                if hasattr(g, "exterior"):
                    outer = g.exterior

                    xpos = np.array(outer.xy[0])
                    ypos = np.array(outer.xy[1])
                    l = levels[n]
                    h = height[n]

                    points = np.zeros((np.shape(outer.xy)[1], 3))
                    points[:, 0] = xpos
                    points[:, 1] = ypos
                    points[:, 0] -= center_offset_x
                    points[:, 1] -= center_offset_y

                    delta_elevation = 0
                    if terrain_mesh:
                        buffer = 50  # additional distance so intersection test is further away than directly on surface
                        bb_terrain = terrain_mesh.bounds
                        start_z = bb_terrain[4] - buffer
                        stop_z = bb_terrain[5] + buffer

                        # The shape files do not have z/elevation position. So for them to align to the
                        # terrain we need to first get the position of the terrain at the xy position of shape file
                        # this will align the buildins so they sit on the terrain no matter the location
                        elevation_on_outline = []

                        # check every point on the building shape for z elevation location
                        for point in points:
                            # shoot ray to look for intersection point
                            start_ray = [point[0], point[1], start_z]
                            stop_ray = [point[0], point[1], stop_z]
                            intersection_point, _ = terrain_mesh.ray_trace(start_ray, stop_ray)
                            if len(intersection_point) != 0:
                                z_surface_location = intersection_point.flatten()[2]
                                elevation_on_outline.append(z_surface_location)
                        # find lowest point on building outline to align location
                        if elevation_on_outline:
                            min_elevation = np.min(elevation_on_outline)
                            max_elevation = np.max(elevation_on_outline)
                            delta_elevation = max_elevation - min_elevation

                            # change z position to minimum elevation of terrain
                            points[:, 2] = min_elevation
                        else:
                            points[:, 2] = start_z

                    num_percent_bins = 40
                    percent = np.round((n + 1) / (len(geo)) * 100, decimals=1)
                    if percent % 10 == 0 and percent != last_displayed:
                        last_displayed = percent
                        perc_done = int(num_percent_bins * percent / 100)
                        perc_left = num_percent_bins - perc_done
                        percent_symbol1 = "." * perc_left
                        percent_symbol2 = "#" * perc_done

                        i = percent_symbol2 + percent_symbol1 + " " + str(percent) + "% "
                        logger.info(f"\rPercent Complete:{i}")

                    # create closed and filled polygon from outline of building
                    roof = self.create_building_roof(points)
                    if np.isnan(float(h)) == False:
                        extrude_h = float(h) * 2
                    elif np.isnan(float(l)) == False:
                        extrude_h = float(l) * 10
                    else:
                        extrude_h = 15.0

                    outline = pv.lines_from_points(points, close=True)

                    vert_walls = outline.extrude([0, 0, extrude_h + delta_elevation], inplace=False)

                    roof_location = np.array([0, 0, extrude_h + delta_elevation])
                    roof.translate(roof_location, inplace=True)

                    building_meshes += vert_walls
                    building_meshes += roof

            el = building_meshes.points[:, 2]

            building_meshes["Elevation"] = el.ravel(order="F")

            file_out = self.cad_path + "\\buildings.stl"
            building_meshes.save(file_out, binary=True)

            return {"file_name": file_out, "mesh": building_meshes, "temp": temp}


class RoadPrep(object):
    """Contains all basic functions needed to generate road stl files."""

    def __init__(self, cad_path):
        self.cad_path = cad_path

    @pyaedt_function_handler()
    def create_roads(self, center_lat_lon, terrain_mesh, max_radius=1000, z_offset=0, road_step=10, road_width=5):
        """Generate the road stl file.

        Parameters
        ----------
        center_lat_lon : list
            Latitude and longitude.
        terrain_mesh : :class:`pyvista.PolygonData`
            Terrain mesh.
        max_radius : float, int
            Radius around latitude and longitude.
        z_offset : float, optional
            Elevation offset of the road.
        road_step : float, optional
            Road computation steps in meters.
        road_width : float, optional
            Road width in meter.

        Returns
        -------
        dict
            Info of generated stl file.
        """
        graph = ox.graph_from_point(
            center_lat_lon, dist=max_radius, simplify=False, network_type="all", clean_periphery=True
        )

        g_projected = ox.project_graph(graph)

        utm_center = utm.from_latlon(center_lat_lon[0], center_lat_lon[1])
        center_offset_x = utm_center[0]
        center_offset_y = utm_center[1]

        _, edges = ox.graph_to_gdfs(g_projected)
        lines = []

        buffer = 10  # additional distance so intersection test is further away than directly on surface
        bb_terrain = terrain_mesh.bounds
        start_z = bb_terrain[4] - buffer
        stop_z = bb_terrain[5] + buffer

        line = pv.PolyData()
        road_ends = pv.PolyData()
        # convert each edge into a line
        count = 0
        last_displayed = -1
        for _, row in edges.iterrows():
            count += 1
            num_percent_bins = 40

            percent = np.round((count) / (len(edges)) * 100, decimals=1)
            if percent % 10 == 0 and percent != last_displayed:
                last_displayed = percent
                perc_done = int(num_percent_bins * percent / 100)
                perc_left = num_percent_bins - perc_done
                percent_symbol1 = "." * perc_left
                percent_symbol2 = "#" * perc_done

                i = percent_symbol2 + percent_symbol1 + " " + str(percent) + "% "
                logger.info(f"\rPercent Complete:{i}")

            x_pts = row["geometry"].xy[0]
            y_pts = row["geometry"].xy[1]
            z_pts = np.empty(len(x_pts))
            z_pts.fill(start_z + z_offset)
            for n in range(len(z_pts)):
                x_pts[n] = x_pts[n] - center_offset_x
                y_pts[n] = y_pts[n] - center_offset_y
                start_ray = [x_pts[n], y_pts[n], start_z]
                stop_ray = [x_pts[n], y_pts[n], stop_z]
                points, _ = terrain_mesh.ray_trace(start_ray, stop_ray)
                if len(points) != 0:
                    z_surface_location = points.flatten()[2]
                    z_pts[n] = z_surface_location + z_offset
            pts = np.column_stack((x_pts, y_pts, z_pts))
            # always 2 points, linear interpolate to higher number of points
            dist = np.sqrt(
                np.power(pts[0][0] - pts[1][0], 2)
                + np.power(pts[0][1] - pts[1][1], 2)
                + np.power(pts[0][2] - pts[1][2], 2)
            )
            if dist > road_step:
                num_steps = int(dist / road_step)
                xpos = np.linspace(pts[0][0], pts[1][0], num=num_steps)
                ypos = np.linspace(pts[0][1], pts[1][1], num=num_steps)
                zpos = np.linspace(pts[0][2], pts[1][2], num=num_steps)
                pts = np.column_stack((xpos, ypos, zpos))
            try:
                line += pv.lines_from_points(pts, close=True)
            except ValueError:
                pass
            end_shape = pv.Circle(road_width, resolution=16).delaunay_2d()
            road_ends += end_shape.translate(pts[0], inplace=False)
            end_shape = pv.Circle(road_width, resolution=16).delaunay_2d()
            road_ends += end_shape.translate(pts[-1], inplace=False)
            lines.append(line)

        roads = line.ribbon(width=road_width, normal=[0, 0, 1])
        roads += road_ends
        el = roads.points[:, 2]

        roads["Elevation"] = el.ravel(order="F")
        file_out = os.path.join(self.cad_path + "\\roads.stl")
        roads.save(file_out)
        return {"file_name": file_out, "mesh": roads, "graph": g_projected}


class TerrainPrep(object):
    """Contains all basic functions needed for creating a terrain stl mesh."""

    def __init__(self, cad_path="./"):
        self.cad_path = cad_path

    @pyaedt_function_handler()
    def get_terrain(self, center_lat_lon, max_radius=500, grid_size=5, buffer_percent=0):
        """Generate the terrain stl file.

        Parameters
        ----------
        center_lat_lon : list
            Latitude and longitude.
        max_radius : float, int
            Radius around latitude and longitude.
        grid_size : float, optional
            Grid size in meters.
        buffer_percent : float, optional
            Buffer extra size over the radius.


        Returns
        -------
        dict
            Info of generated stl file.
        """
        utm_center = utm.from_latlon(center_lat_lon[0], center_lat_lon[1])
        logger.info("Generating Terrain")
        max_radius = max_radius * (buffer_percent + 1)
        all_data, _, all_utm = self.get_elevation(
            center_lat_lon,
            max_radius=max_radius,
            grid_size=grid_size,
        )

        all_data = np.nan_to_num(all_data, nan=-32768)
        logger.info("Processing Geometry")
        xyz = []
        for lat_idx in range(all_data.shape[0]):
            for lon_idx in range(all_data.shape[1]):
                latlat_utm_centered = all_utm[lat_idx][lon_idx][0] - utm_center[0]
                lonlon_utm_centered = all_utm[lat_idx][lon_idx][1] - utm_center[1]

                if (
                    all_data[lat_idx][lon_idx] != -32768
                ):  # this is missing data from srtm, don't add if it doesn't exist
                    xyz.append([latlat_utm_centered, lonlon_utm_centered, all_data[lat_idx][lon_idx]])
        xyz = np.array(xyz)

        file_out = self.cad_path + "/terrain.stl"
        logger.info("saving STL as " + file_out)
        terrain_mesh = pv.PolyData(xyz)
        terrain_mesh = terrain_mesh.delaunay_2d(
            tol=10 / (2 * max_radius) / 2
        )  # tolerance, srtm is 30meter, so as a fraction of total size this would be 30/2/radius
        terrain_mesh = terrain_mesh.smooth(n_iter=100, relaxation_factor=0.04)

        el = terrain_mesh.points[:, 2]

        terrain_mesh["Elevation"] = el.ravel(order="F")

        terrain_mesh.save(file_out)
        return {"file_name": file_out, "mesh": terrain_mesh}

    @staticmethod
    @pyaedt_function_handler()
    def get_elevation(
        center_lat_lon,
        max_radius=500,
        grid_size=3,
    ):
        """Get Elevation map.

        Parameters
        ----------
        center_lat_lon : list
            Latitude and longitude.
        max_radius : float, int
            Radius around latitude and longitude.
        grid_size : float, optional
            Grid size in meters.

        Returns
        -------
        tuple
        """
        utm_center = utm.from_latlon(center_lat_lon[0], center_lat_lon[1])
        # assume never at boundary of zone number or letter
        zone_letter = utm.latitude_to_zone_letter(center_lat_lon[0])
        zone_number = utm.latlon_to_zone_number(center_lat_lon[0], center_lat_lon[1])
        logger.info(zone_letter)
        logger.info(zone_number)
        logger.info(utm_center)
        utm_x_min = utm_center[0] - max_radius
        utm_x_max = utm_center[0] + max_radius

        utm_y_min = utm_center[1] - max_radius
        utm_y_max = utm_center[1] + max_radius

        sample_grid_size = grid_size  # meters
        num_samples = int(np.ceil(max_radius * 2 / sample_grid_size))
        x_samples = np.linspace(utm_x_min, utm_x_max, int(num_samples))
        y_samples = np.linspace(utm_y_min, utm_y_max, int(num_samples))
        elevation_data = srtm.get_data()

        all_data = np.zeros((num_samples, num_samples))
        all_utm = np.zeros((num_samples, num_samples, 2))
        all_lat_lon = np.zeros((num_samples, num_samples, 2))
        logger.info("Terrain Points...")
        last_displayed = -1
        for n, x in enumerate(x_samples):
            for m, y in enumerate(y_samples):
                num_percent_bins = 40

                percent_complete = int((n * num_samples + m) / (num_samples * num_samples) * 100)
                if percent_complete % 10 == 0 and percent_complete != last_displayed:
                    last_displayed = percent_complete
                    perc_done = int(num_percent_bins * percent_complete / 100)
                    perc_left = num_percent_bins - perc_done
                    percent_symbol1 = "." * perc_left
                    percent_symbol2 = "#" * perc_done
                    i = percent_symbol2 + percent_symbol1 + " " + str(percent_complete) + "% "
                    logger.info(f"\rPercent Complete:{i}")
                zone_letter = utm.latitude_to_zone_letter(center_lat_lon[0])
                zone_number = utm.latlon_to_zone_number(center_lat_lon[0], center_lat_lon[1])
                current_lat_lon = utm.to_latlon(x, y, zone_number, zone_letter)
                all_data[n, m] = elevation_data.get_elevation(current_lat_lon[0], current_lat_lon[1])
                all_lat_lon[n, m] = current_lat_lon
                all_utm[n, m] = [x, y]
        logger.info(str(100) + "% - Done")
        return all_data, all_lat_lon, all_utm
