import os

from flask import Flask, Response, render_template

from . import db, news, tasks_api, weather


def create_app():
    app = Flask(__name__)
    app.json.ensure_ascii = False
    db.init_db()
    app.register_blueprint(tasks_api.bp)
    app.register_blueprint(news.bp)
    app.register_blueprint(weather.bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/help")
    def help_page():
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs",
            "user-guide.md",
        )
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            text = "Инструкция недоступна."
        return Response(text, mimetype="text/plain; charset=utf-8")

    return app


app = create_app()
