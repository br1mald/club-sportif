from flask import Flask

from config import Config
from db import close_db
from routes.competitions import competitions_bp
from routes.cotisations import cotisations_bp
from routes.dashboard import dashboard_bp
from routes.entrainements import entrainements_bp
from routes.membres import membres_bp


def create_app(config_class=Config):
    app = Flask(__name__)

    app.config.from_object(config_class)

    app.teardown_appcontext(close_db)

    if not app.config["DB_CONFIG"].get("password"):
        raise ValueError("No password set in .env")

    app.register_blueprint(membres_bp)
    app.register_blueprint(entrainements_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(cotisations_bp)
    app.register_blueprint(competitions_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
