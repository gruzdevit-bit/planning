import math
import os
import threading
import time

import requests
from flask import Blueprint, jsonify, request

from . import db

bp = Blueprint("weather_api", __name__)

WEATHER_ERROR = "Прогноз погоды временно недоступен"
GEO_ERROR = "Не удалось выполнить поиск города"

_cache = {}
_lock = threading.Lock()


class WeatherError(Exception):
    pass


def reset_cache():
    with _lock:
        _cache.clear()


def round_half_away(value):
    """Округление до целого: 4.6 -> 5, -3.5 -> -4, -0.4 -> 0."""
    number = float(value)
    result = int(math.floor(abs(number) + 0.5))
    return -result if number < 0 else result


def temp_label(n):
    if n > 0:
        return "+%d" % n
    if n < 0:
        return "-%d" % abs(n)
    return "0"


def format_temp(value):
    return temp_label(round_half_away(value))


def parse_daily(payload):
    try:
        daily = payload["daily"]
        dates = daily["time"]
        temps = daily["temperature_2m_max"]
    except (KeyError, TypeError):
        raise WeatherError("bad payload")
    days = {}
    for date, value in zip(dates, temps):
        if value is None:
            continue
        try:
            n = round_half_away(value)
        except (TypeError, ValueError):
            continue
        days[date] = {"temp": n, "label": temp_label(n)}
    return days


def get_json(url, params):
    timeout = float(os.environ.get("WEATHER_TIMEOUT", "5"))
    try:
        resp = requests.get(
            url,
            params=params,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (Daily planner)"},
        )
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError) as exc:
        raise WeatherError(str(exc))


def fetch_forecast(lat, lon):
    url = os.environ.get("WEATHER_URL", "https://api.open-meteo.com/v1/forecast")
    ttl = float(os.environ.get("WEATHER_TTL", "1800"))
    key = (round(float(lat), 3), round(float(lon), 3))
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < ttl:
            return hit[1]
    payload = get_json(
        url,
        {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max",
            "timezone": "auto",
            "forecast_days": 16,
        },
    )
    days = parse_daily(payload)
    with _lock:
        _cache[key] = (time.time(), days)
    return days


def search_cities(query):
    url = os.environ.get("GEOCODE_URL", "https://geocoding-api.open-meteo.com/v1/search")
    data = get_json(url, {"name": query, "count": 8, "language": "ru", "format": "json"})
    results = data.get("results") if isinstance(data, dict) else None
    out = []
    for r in results or []:
        try:
            out.append(
                {
                    "name": str(r["name"]),
                    "latitude": float(r["latitude"]),
                    "longitude": float(r["longitude"]),
                    "timezone": str(r.get("timezone") or "auto"),
                    "country": str(r.get("country") or ""),
                    "admin": str(r.get("admin1") or ""),
                }
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return out


def clean_city(data):
    if not isinstance(data, dict):
        return None
    name = data.get("name")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        return None
    try:
        lat = float(data.get("latitude"))
        lon = float(data.get("longitude"))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    tz = data.get("timezone")
    country = data.get("country")
    admin = data.get("admin")
    return {
        "name": name.strip(),
        "latitude": lat,
        "longitude": lon,
        "timezone": tz if isinstance(tz, str) and tz else "auto",
        "country": country if isinstance(country, str) else "",
        "admin": admin if isinstance(admin, str) else "",
    }


@bp.get("/api/geocode")
def geocode():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2 or len(q) > 100:
        return jsonify([])
    try:
        return jsonify(search_cities(q))
    except WeatherError:
        return jsonify({"error": GEO_ERROR}), 502


@bp.get("/api/settings")
def get_settings():
    return jsonify({"city": db.get_city()})


@bp.put("/api/settings/city")
def put_city():
    city = clean_city(request.get_json(silent=True))
    if city is None:
        return jsonify({"error": "Некорректные данные города"}), 400
    db.set_city(city)
    return jsonify(city)


@bp.get("/api/weather")
def get_weather():
    city = db.get_city()
    if not city:
        return jsonify({"city": None, "days": {}})
    try:
        days = fetch_forecast(city["latitude"], city["longitude"])
    except (WeatherError, KeyError, TypeError, ValueError):
        return jsonify({"error": WEATHER_ERROR}), 502
    return jsonify({"city": city, "days": days})
