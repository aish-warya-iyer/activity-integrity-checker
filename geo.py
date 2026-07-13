import polyline as polyline_lib
import pyproj
from shapely.geometry import LineString, Point

DEFAULT_THRESHOLD_M = 15.0


def decode_polyline(encoded):
    return polyline_lib.decode(encoded)


def _metric_transformer(center_lat, center_lon):
    aeqd_crs = pyproj.CRS.from_proj4(
        f"+proj=aeqd +lat_0={center_lat} +lon_0={center_lon} "
        "+x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"
    )
    wgs84 = pyproj.CRS.from_epsg(4326)
    return pyproj.Transformer.from_crs(wgs84, aeqd_crs, always_xy=True)


def compute_segment_deviation(segment_polyline_encoded, actual_latlng_points, threshold_m=DEFAULT_THRESHOLD_M):
    official_points = decode_polyline(segment_polyline_encoded)
    if len(official_points) < 2 or not actual_latlng_points:
        return {"max_deviation_m": None, "flagged": False, "reason": "insufficient_data"}

    center_lat = sum(p[0] for p in official_points) / len(official_points)
    center_lon = sum(p[1] for p in official_points) / len(official_points)
    transformer = _metric_transformer(center_lat, center_lon)

    def to_xy(lat, lon):
        return transformer.transform(lon, lat)

    official_line = LineString([to_xy(lat, lon) for lat, lon in official_points])
    deviations = [official_line.distance(Point(to_xy(lat, lon))) for lat, lon in actual_latlng_points]
    max_deviation = max(deviations)

    return {
        "max_deviation_m": round(max_deviation, 2),
        "flagged": max_deviation > threshold_m,
        "threshold_m": threshold_m,
        "num_points_checked": len(deviations),
    }
