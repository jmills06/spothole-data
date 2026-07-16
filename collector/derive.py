import math
from config import QTH, EARTH_RADIUS_MI


def haversine_mi(lat1, lon1, lat2, lon2):
    r = EARTH_RADIUS_MI
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)), 1)


def enrich(spot):
    """Add derived fields in place and return the spot."""
    # CQ zone match against home QTH (activator's zone; see caveat in README).
    zone = spot.get("dx_cq_zone")
    spot["in_my_cq_zone"] = (zone == QTH["cq_zone"]) if zone is not None else None

    # Distance is only trustworthy when the location is good; otherwise null,
    # so boards never show a confident distance for a DXCC-centroid guess.
    lat, lon = spot.get("dx_latitude"), spot.get("dx_longitude")
    if spot.get("dx_location_good") and lat is not None and lon is not None:
        spot["distance_from_qth_mi"] = haversine_mi(QTH["lat"], QTH["lon"], lat, lon)
    else:
        spot["distance_from_qth_mi"] = None
    return spot


def _matches(spot, match):
    for key, want in match.items():
        val = spot.get(key)
        if isinstance(want, list):
            if val not in want:
                return False
        elif val != want:
            return False
    return True


def _dedupe_latest_per_call(spots):
    latest = {}
    for s in spots:
        call = s.get("dx_call")
        if call is None:
            continue
        if call not in latest or (s.get("time") or 0) > (latest[call].get("time") or 0):
            latest[call] = s
    return list(latest.values())


def build_slice(master, feed):
    rows = [s for s in master if _matches(s, feed["match"])]
    if feed.get("dedupe"):
        rows = _dedupe_latest_per_call(rows)
    rows.sort(key=lambda s: s.get("time") or 0, reverse=True)  # newest first
    return rows
