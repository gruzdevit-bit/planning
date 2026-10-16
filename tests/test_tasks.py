def make(client, **kw):
    body = {"title": "Купить хлеб", "date": "2025-05-14", "time": "18:00"}
    body.update(kw)
    return client.post("/api/tasks", json=body)


def test_index_alive(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Ежедневник" in r.get_data(as_text=True)


def test_create_and_list(client):
    r = make(client)
    assert r.status_code == 201
    assert r.get_json()["time"] == "18:00"
    items = client.get("/api/tasks?date=2025-05-14").get_json()
    assert [t["title"] for t in items] == ["Купить хлеб"]
    assert client.get("/api/tasks/days?month=2025-05").get_json() == ["2025-05-14"]


def test_empty_title_rejected(client):
    r = make(client, title="   ")
    assert r.status_code == 400
    assert r.get_json()["error"] == "Название дела обязательно"
    assert client.get("/api/tasks?date=2025-05-14").get_json() == []


def test_toggle_done(client):
    tid = make(client).get_json()["id"]
    r = client.patch(f"/api/tasks/{tid}/done", json={"done": True})
    assert r.get_json()["done"] is True
    items = client.get("/api/tasks?date=2025-05-14").get_json()
    assert len(items) == 1 and items[0]["done"] is True
    r = client.patch(f"/api/tasks/{tid}/done", json={"done": False})
    assert r.get_json()["done"] is False


def test_edit_keeps_date_and_time(client):
    tid = make(client).get_json()["id"]
    r = client.put(f"/api/tasks/{tid}", json={"title": "Купить хлеб и молоко"})
    data = r.get_json()
    assert data["title"] == "Купить хлеб и молоко"
    assert data["date"] == "2025-05-14"
    assert data["time"] == "18:00"


def test_delete_removes_mark(client):
    tid = make(client).get_json()["id"]
    assert client.delete(f"/api/tasks/{tid}").status_code == 204
    assert client.get("/api/tasks?date=2025-05-14").get_json() == []
    assert client.get("/api/tasks/days?month=2025-05").get_json() == []
    assert client.delete(f"/api/tasks/{tid}").status_code == 404


def test_persistence(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import create_app

    c1 = create_app().test_client()
    c1.post("/api/tasks", json={"title": "Дело", "date": "2025-06-01", "time": "09:30"})
    c2 = create_app().test_client()
    items = c2.get("/api/tasks?date=2025-06-01").get_json()
    assert items[0]["title"] == "Дело" and items[0]["time"] == "09:30"


def test_only_selected_day(client):
    make(client, title="А", date="2025-05-14")
    make(client, title="Б", date="2025-05-21", time=None)
    items = client.get("/api/tasks?date=2025-05-21").get_json()
    assert [t["title"] for t in items] == ["Б"]


def test_sorting_time_first(client):
    make(client, title="Без времени", time=None)
    make(client, title="Поздно", time="20:00")
    make(client, title="Рано", time="08:00")
    items = client.get("/api/tasks?date=2025-05-14").get_json()
    assert [t["title"] for t in items] == ["Рано", "Поздно", "Без времени"]
