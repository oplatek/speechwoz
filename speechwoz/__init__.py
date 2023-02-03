import os

from flask import Flask


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        VERSION="0.0.1",
        # a default secret that should be overridden by instance config
        SECRET_KEY="dev",
        # store the database in the instance folder
        DATABASE=os.path.join(app.instance_path, "speechwoz.sqlite"),
        # Number to be called to connect
        # So far enabled for Czech republic and I think also by default for US
        # https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
        TWILIO_NUMBER="+420910902780",
        PROLIFIC_CODE="TODO_paste_code_to_be_displayed_to_workers",
    )
    assert "TWILIO_NUMBER" in app.config

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    @app.route("/hello")
    def hello():
        return "Hello, World!"

    # register the database commands
    from speechwoz import db

    db.init_app(app)

    return app
