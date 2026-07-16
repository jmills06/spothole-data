import json, os, time, datetime as dt
import spothole, derive
from config import MASTER_SPOTS_PARAMS, DERIVED_FEEDS, SIMPLE_FEEDS, QTH, DISTANCE_UNIT

LATEST = "data/latest"
HIST_DIR = "data/history/spots"
STATE = "data/history/state.json"


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def _as_list(spots_payload):
    # Normalize after live-verifying the real shape (bare list vs wrapped).
    if isinstance(spots_payload, list):
        return spots_payload
    for key in ("spots", "data", "results"):
        if isinstance(spots_payload, dict) and isinstance(spots_payload.get(key), list):
            return spots_payload[key]
    raise ValueError("Unexpected /spots shape; inspect and update _as_list")


def main():
    now = int(time.time())
    feeds_meta = {}

    # --- Master spots ---
    master = []
    try:
        master = [derive.enrich(s) for s in _as_list(spothole.get("/spots", MASTER_SPOTS_PARAMS, use_qrz=True))]
        master.sort(key=lambda s: s.get("time") or 0, reverse=True)
        _write_json(f"{LATEST}/spots.json", master)
        feeds_meta["spots"] = {"url": "data/latest/spots.json", "count": len(master), "updated": now, "ok": True}
    except Exception as e:
        print(f"[master] FAILED, keeping previous file: {e}")
        feeds_meta["spots"] = {"url": "data/latest/spots.json", "ok": False}

    # --- Derived slices ---
    for feed in DERIVED_FEEDS:
        try:
            rows = derive.build_slice(master, feed)
            _write_json(f"{LATEST}/{feed['name']}.json", rows)
            feeds_meta[feed["name"]] = {"url": f"data/latest/{feed['name']}.json", "count": len(rows), "updated": now, "ok": True}
        except Exception as e:
            print(f"[{feed['name']}] FAILED: {e}")
            feeds_meta[feed["name"]] = {"url": f"data/latest/{feed['name']}.json", "ok": False}

    # --- History append (only spots new since last run) ---
    try:
        last_received = 0
        if os.path.exists(STATE):
            last_received = json.load(open(STATE)).get("last_received", 0)
        new = [s for s in master if (s.get("received_time") or 0) > last_received]
        if new:
            day = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
            path = f"{HIST_DIR}/{day}.jsonl"
            os.makedirs(HIST_DIR, exist_ok=True)
            seen = set()
            if os.path.exists(path):
                for line in open(path, encoding="utf-8"):
                    try: seen.add(json.loads(line).get("id"))
                    except Exception: pass
            with open(path, "a", encoding="utf-8") as f:
                for s in new:
                    if s.get("id") not in seen:
                        f.write(json.dumps(s, ensure_ascii=False, separators=(",", ":")) + "\n")
        if master:
            hi = max((s.get("received_time") or 0) for s in master)
            _write_json(STATE, {"last_received": max(hi, last_received)})
    except Exception as e:
        print(f"[history] FAILED: {e}")

    # --- Simple feeds (own shape) ---
    for feed in SIMPLE_FEEDS:
        try:
            payload = spothole.get(feed["path"], use_qrz=feed["qrz"])
            _write_json(f"{LATEST}/{feed['name']}.json", payload)
            count = len(payload) if isinstance(payload, list) else None
            feeds_meta[feed["name"]] = {"url": f"data/latest/{feed['name']}.json", "count": count, "updated": now, "ok": True}
        except Exception as e:
            print(f"[{feed['name']}] FAILED, keeping previous file: {e}")
            feeds_meta[feed["name"]] = {"url": f"data/latest/{feed['name']}.json", "ok": False}

    # --- Manifest ---
    manifest = {
        "generated": now,
        "generated_iso": dt.datetime.fromtimestamp(now, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": 1,
        "distance_unit": DISTANCE_UNIT,
        "qth": QTH,
        "feeds": feeds_meta,
    }
    _write_json(f"{LATEST}/manifest.json", manifest)
    print("Done.")


if __name__ == "__main__":
    main()
