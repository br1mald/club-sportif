from flask import Flask

from config import Config
from db import close_db


def create_app(config_class=Config):
    app = Flask(__name__)

    app.config.from_object(config_class)

    app.teardown_appcontext(close_db)

    if not app.config["DB_CONFIG"].get("password"):
        raise ValueError("No password set in .env")

    # app.register_blueprint()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
