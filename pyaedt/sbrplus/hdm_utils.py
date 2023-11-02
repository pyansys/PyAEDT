def sort_bundle(bundle, monoPW_attrib="sweep_angle_index"):
    """In-place sorting utility for hdm ray exports.

    Ray exports are not guaranteed to always be in a predermined order,
    because of the non-deterministic multi-threaded SBR+ solver implementation.

    SBR+ rays will be sorted by source launch point, UTD bright point if present,
    and first-bounce ray hit point. In the case of monostatic PW incidence, the launch
    point is represented by the sweep angle index.

    Creeping rays will be sorted by source launch point, geodesic origin,
    and first-footprint current location. In the case of monostatic PW incidence, the launch
    point is represented by the sweep angle index.

    :param bundle: SBR+ or CW bundle from hdm_parser
    :param str monoPW_attrib: sweep angle index argument name for monostatic PW illumination
    """
    if bundle.__name__ == "CreepingWave":
        if hasattr(bundle.creeping_rays[0], monoPW_attrib):
            key = lambda ray: (
                getattr(ray, monoPW_attrib),
                ray.geodesic_origin.tolist(),
                ray.footprints[0].currents_position.tolist(),
            )
        else:
            key = lambda ray: (
                ray.source_point.tolist(),
                ray.geodesic_origin.tolist(),
                ray.footprints[0].currents_position.tolist(),
            )
        bundle.creeping_rays.sort(key=key)
    elif bundle.__name__ == "Bundle":
        if hasattr(bundle.ray_tracks[0], monoPW_attrib):
            key = lambda ray: (
                getattr(ray, monoPW_attrib),
                ray.utd_point.tolist() if ray.utd_point is not None else ray.source_point.tolist(),
                ray.first_bounce.hit_pt.tolist(),
            )
        else:
            key = lambda ray: (
                ray.source_point.tolist(),
                ray.utd_point.tolist() if ray.utd_point is not None else ray.source_point.tolist(),
                ray.first_bounce.hit_pt.tolist(),
            )
        bundle.ray_tracks.sort(key=key)
