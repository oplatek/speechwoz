# speechwoz


This is development documentation (becomes outdated).


## Usage

### Run on namuddis
```
# Relevat part of /etc/apache2/sites-available/000-default.conf

# speechwoz on port 8090
# Details of deployment at https://dlukes.github.io/flask-wsgi-url-prefix.html
# TL;DR use
# SCRIPT_NAME=/namuddis/speechwoz gunicorn app:app --bind 127.0.0.1:8090
# For apps like 
ProxyPass /speechwoz http://127.0.0.1:8090/namuddis/speechwoz
ProxyPassReverse /speechwoz http://127.0.0.1:8090/namuddis/speechwoz
```

```
# From repo root
SCRIPT_NAME=/namuddis/speechwoz gunicorn speechwoz:create_app --bind 127.0.0.1:8090 -w 4
```


### Run locally

```
$ flask --app speechwoz init-db
$ flask --app speechwoz run --debug
```
Open http://127.0.0.1:5000 in a browser.

### Test

```
$ pip install '.[test]'
$ pytest
```

### Run with coverage report:

```
$ coverage run -m pytest
$ coverage report
$ coverage html  # open htmlcov/index.html in a browser
```

## Links
- [Spoken MultiWOZ Recording Application Gdoc](https://docs.google.com/document/d/1VZF8d69vjUBFtEB5uzqVi8E7csa0CQR5AthQrzqK7AM/)
- MultiWoz 2.1 s messages  "/lnet/work/people/odusek/diaser/source_diaser_data/multiwoz/data/MultiWOZ_2.1//"
- github.com/oplatek/twilio-browser-calls-flask branch WIP dial.py demonstrate minimal example of saving recording
- Chat app based on FlaskIO should be the backbone of our app https://github.com/miguelgrinberg/Flask-SocketIO-Chat
- Html5 speech recorder https://github.com/duketemon/web-speech-recorder.git  for recording audio
- https://github.com/apm1467/html5-mic-visualizer


### Streamlit prototype
- useful now only for Lhotse usage demo
- WebRTC is not a good transport layer/protocol for saving high quality audio
