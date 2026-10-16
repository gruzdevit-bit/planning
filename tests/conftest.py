import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import create_app
    from app import news, weather

    news.reset_cache()
    weather.reset_cache()
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()
