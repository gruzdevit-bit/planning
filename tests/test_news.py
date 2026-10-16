import requests

from app import news

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
{items}
</channel></rss>"""

ITEM = (
    "<item><title>Новость {n}</title><link>https://lenta.ru/news/{n}/</link>"
    "<pubDate>Wed, 14 May 2025 09:{n:02d}:00 +0300</pubDate></item>"
)


class FakeResp:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


def test_news_ten_items(client, monkeypatch):
    xml = RSS.format(items="".join(ITEM.format(n=i) for i in range(15)))
    monkeypatch.setattr(news.requests, "get", lambda *a, **k: FakeResp(xml.encode("utf-8")))
    r = client.get("/api/news")
    assert r.status_code == 200
    data = r.get_json()
    assert len(data) == 10
    assert data[0]["title"] == "Новость 0"
    assert data[0]["url"].startswith("https://lenta.ru/")
    assert "2025-05-14T09:00:00+03:00" == data[0]["published"]


def test_news_failure(client, monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(news.requests, "get", boom)
    r = client.get("/api/news")
    assert r.status_code == 502
    assert r.get_json()["error"] == "Не удалось загрузить новости"
    assert client.get("/").status_code == 200
    assert client.get("/api/tasks?date=2025-05-14").status_code == 200
