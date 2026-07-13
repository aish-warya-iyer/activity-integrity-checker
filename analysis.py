import geo
import strava


def analyze_activity(activity_id, threshold_m=geo.DEFAULT_THRESHOLD_M):
    detail = strava.api_get(f"/activities/{activity_id}", params={"include_all_efforts": "true"})
    streams = strava.api_get(
        f"/activities/{activity_id}/streams",
        params={"keys": "latlng,distance,time", "key_by_type": "true"},
    )
    latlng_stream = streams.get("latlng", {}).get("data", [])

    results = []
    for effort in detail.get("segment_efforts", []):
        segment_id = effort["segment"]["id"]
        start_idx = effort.get("start_index")
        end_idx = effort.get("end_index")
        if start_idx is None or end_idx is None:
            continue

        actual_points = latlng_stream[start_idx : end_idx + 1]
        segment_detail = strava.api_get(f"/segments/{segment_id}")
        segment_polyline = segment_detail.get("map", {}).get("polyline")
        if not segment_polyline:
            continue

        deviation = geo.compute_segment_deviation(segment_polyline, actual_points, threshold_m=threshold_m)
        results.append(
            {
                "segment_id": segment_id,
                "segment_name": effort["segment"].get("name"),
                "effort_id": effort["id"],
                **deviation,
            }
        )

    return results
