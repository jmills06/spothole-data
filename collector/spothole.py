import os
import requests
from config import API_BASE, USER_AGENT

# (connect, read) timeout in seconds. Connect stays short so a genuinely
# dead server fails fast; read is generous because QRZ enrichment on
# Spothole's side does a per-callsign XML lookup and can be slow on a
# broad pull, especially while its callsign cache is cold.
HTTP_TIMEOUT = (10, 180)


def _qrz_params():
    u, p = os.environ.get("QRZ_USERNAME"), os.environ.get("QRZ_PASSWORD")
    return {"qrz_username": u, "qrz_password": p} if u and p else {}


def get(path, params=None, use_qrz=False):
    params = dict(params or {})
    if use_qrz:
        params.update(_qrz_params())
    resp = requests.get(
        f"{API_BASE}{path}",
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=HTTP_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()
