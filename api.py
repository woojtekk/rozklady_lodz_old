from __future__ import annotations
from typing import Any, Dict
import re
from xml.etree import ElementTree as ET
from aiohttp import ClientSession, ClientTimeout

NUM_RE = re.compile(r"\d+")

def _digits(s: str | None) -> int | None:
    if not s:
        return None
    m = NUM_RE.search(s)
    return int(m.group()) if m else None

def _to_int(s: str | None) -> int | None:
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return _digits(s)

def _hhmm_to_minutes(hhmm: str) -> int | None:
    try:
        hh, mm = hhmm.split(":")
        return int(hh)*60 + int(mm)
    except Exception:
        return None

class RozkladyAPI:
    """Async client for rozklady.lodz.pl realtime endpoint (minutes derived from seconds)."""

    def __init__(self, session: ClientSession, base_url: str) -> None:
        self._session = session
        self._base = base_url

    async def fetch_xml(self, stop_number: int, timeout: float = 10.0) -> bytes:
        params = {"busStopNum": str(stop_number)}
        headers = {"User-Agent": "HomeAssistant/rozklady_lodz (https://www.home-assistant.io/)"}
        to = ClientTimeout(total=timeout)
        async with self._session.get(self._base, params=params, headers=headers, timeout=to) as resp:
            resp.raise_for_status()
            return await resp.read()

    def parse(self, xml_bytes: bytes, only_trams: bool = True) -> Dict[str, Any]:
        root = ET.fromstring(xml_bytes)

        server_time = (root.attrib.get("time") or "").strip()
        server_minutes = _hhmm_to_minutes(server_time) if server_time else None

        stop = root.find(".//Stop")
        stop_name = stop.attrib.get("name", "") if stop is not None else ""

        result: Dict[str, Any] = {"stop_name": stop_name, "server_time": server_time, "departures": {}}

        for r in root.findall(".//R"):
            vt = (r.attrib.get("vt") or "").strip()
            if only_trams and vt and vt != "T":
                continue

            line = (r.attrib.get("nr") or "").strip()
            direction = (r.attrib.get("dir") or "").strip()

            items = []
            for s in r.findall("./S"):
                th = (s.attrib.get("th") or "").strip()
                tm = (s.attrib.get("tm") or "").strip()
                t = (s.attrib.get("t") or "").strip()
                m_attr = (s.attrib.get("m") or "").strip()
                s_attr = (s.attrib.get("s") or "").strip()

                # --- Źródło prawdy: sekundy (s) → minuty (zaokrąglenie w górę) ---
                minutes = None
                s_val = _to_int(s_attr)
                if s_val is not None:
                    minutes = max(0, (s_val + 59) // 60)

                # Fallback #1: oficjalne „m” (minuty)
                if minutes is None:
                    minutes = _to_int(m_attr)

                # Fallback #2: jeśli mamy czas absolutny i czas serwera – różnica mod 24h
                if minutes is None and server_minutes is not None and th and tm:
                    try:
                        dep_total = (int(th)*60 + int(tm)) % (24*60)
                        minutes = (dep_total - server_minutes) % (24*60)
                    except Exception:
                        minutes = _digits(tm)

                # Fallback #3: cyfry z "tm" (np. "2 min")
                if minutes is None:
                    minutes = _digits(tm)

                # Tekst „ładny”
                if th:
                    main = f"{th}:{tm.zfill(2) if tm else '00'}"
                else:
                    main = tm or (str(minutes) + " min" if minutes is not None else "")
                pretty = f"{main} [t={t}, m={m_attr}]".strip()

                items.append({
                    "th": th, "tm": tm, "t": t,
                    "m": _to_int(m_attr),
                    "seconds": s_val,
                    "minutes": minutes,
                    "pretty": pretty,
                })

            items.sort(key=lambda x: (x["minutes"] is None, x["minutes"] if x["minutes"] is not None else 10**9))

            if line not in result["departures"]:
                result["departures"][line] = {"dir": direction, "items": items}
            else:
                result["departures"][line]["items"].extend(items)
                if not result["departures"][line]["dir"] and direction:
                    result["departures"][line]["dir"] = direction

        return result
