# Home QTH — Clarkston MI post office, a public-space proxy for the home location.
QTH = {
    "call": "K8JKU",
    "lat": 42.72285220808688,
    "lon": -83.41970398420766,
    "cq_zone": 4,
}

DISTANCE_UNIT = "mi"          # miles
EARTH_RADIUS_MI = 3958.7613

API_BASE = "https://spothole.app/api/v1"
USER_AGENT = "spothole-data-collector/1.0 (+https://github.com/jmills06/spothole-data; K8JKU)"
HTTP_TIMEOUT = 30

# Master spot pull: all outdoor-programme activity. Excludes general DX / RBN firehose.
MASTER_SPOTS_PARAMS = {"needs_sig": "true"}

# Derived feeds are applied LOCALLY to the master list — no extra API calls.
# Each key in "match" is ANDed. A list value means "value is in list".
# dedupe=True keeps only the latest spot per dx_call (by time).
DERIVED_FEEDS = [
    {"name": "pota",       "match": {"sig": "POTA"},                 "dedupe": True},
    {"name": "ssb",        "match": {"mode": ["SSB", "USB", "LSB"]}, "dedupe": True},
    {"name": "map-points", "match": {"dx_location_good": True},      "dedupe": False},
]

# Feeds that get their own file with their own shape (not spot slices).
# Each entry: endpoint path, output filename, whether QRZ creds apply.
SIMPLE_FEEDS = [
    {"name": "alerts",  "path": "/alerts",  "qrz": True},
    {"name": "solar",   "path": "/solar",   "qrz": False},
    {"name": "dxstats", "path": "/dxstats", "qrz": False},
    {"name": "options", "path": "/options", "qrz": False},
]
