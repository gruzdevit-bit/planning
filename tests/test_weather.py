import requests

from app import weather

MOSCOW = {
    "name": "Москва",
    "latitude": 55.75,
    "longitude": 37.62,
    "timezone": "Europe/Moscow",
    "country": "Россия",
    "admin": "Москва",
}


class FakeResp:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def forecast(dates, temps):
    return {"daily": {"time": dates, "temperature_2m_max": temps}}


def test_format_plus_minus_zero_round():
    assert weather.format_temp(5) == "+5"
    assert weather.format_temp(-3) == "-3"
    assert weather.format_temp(0) == "0"
    assert weather.format_temp(4.6) == "+5"
    assert weather.format_temp(-0.4) == "0"
    assert weather.format_temp(-3.6) == "-4"


def test_parse_daily_skips_missing():
    days = weather.parse_daily(
        forecast(["2025-05-14", "2025-05-15", "2025-05-16"], [4.6, None, -3])
    )
    assert days["2025-05-14"]["label"] == "+5"
    assert "2025-05-15" not in days
    assert days["2025-05-16"]["label"] == "-3"


def test_no_city_no_weather(client):
    assert client.get("/api/settings").get_json() == {"city": None}
    data = client.get("/api/weather").get_json()
    assert data == {"city": None, "days": {}}


def test_save_city_and_persist(client):
    r = client.put("/api/settings/city", json=MOSCOW)
    assert r.status_code == 200
    assert client.get("/api/settings").get_json()["city"]["name"] == "Москва"


def test_bad_city_rejected(client):
    r = client.put("/api/settings/city", json={"name": "", "latitude": 1, "longitude": 1})
    assert r.status_code == 400
    assert client.get("/api/settings").get_json() == {"city": None}


def test_weather_for_city(client, monkeypatch):
    client.put("/api/settings/city", json=MOSCOW)
    payload = forecast(["2025-05-14", "2025-05-15", "2025-05-16"], [5, 0, -3])
    monkeypatch.setattr(weather.requests, "get", lambda *a, **k: FakeResp(payload))
    data = client.get("/api/weather").get_json()
    assert data["city"]["name"] == "Москва"
    assert data["days"]["2025-05-14"]["label"] == "+5"
    assert data["days"]["2025-05-15"]["label"] == "0"
    assert data["days"]["2025-05-16"]["label"] == "-3"


def test_weather_failure_502(client, monkeypatch):
    client.put("/api/settings/city", json=MOSCOW)

    def boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(weather.requests, "get", boom)
    r = client.get("/api/weather")
    assert r.status_code == 502
    assert r.get_json()["error"] == "Прогноз погоды временно недоступен"
    assert client.get("/").status_code == 200
    assert client.get("/api/tasks?date=2025-05-14").status_code == 200


def test_weather_cached(client, monkeypatch):
    client.put("/api/settings/city", json=MOSCOW)
    calls = []

    def fake(*a, **k):
        calls.append(1)
        return FakeResp(forecast(["2025-05-14"], [5]))

    monkeypatch.setattr(weather.requests, "get", fake)
    client.get("/api/weather")
    client.get("/api/weather")
    assert len(calls) == 1


def test_geocode_found_and_empty(client, monkeypatch):
    found = {"results": [{"name": "Москва", "latitude": 55.75, "longitude": 37.62,
                          "timezone": "Europe/Moscow", "country": "Россия", "admin1": "Москва"}]}
    monkeypatch.setattr(weather.requests, "get", lambda *a, **k: FakeResp(found))
    items = client.get("/api/geocode?q=Москва").get_json()
    assert items[0]["name"] == "Москва" and items[0]["latitude"] == 55.75
    monkeypatch.setattr(weather.requests, "get", lambda *a, **k: FakeResp({}))
    assert client.get("/api/geocode?q=Ыыыыыы").get_json() == []


def test_geocode_failure_502(client, monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(weather.requests, "get", boom)
    r = client.get("/api/geocode?q=Москва")
    assert r.status_code == 502
