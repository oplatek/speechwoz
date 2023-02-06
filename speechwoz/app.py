import os
from pathlib import Path
import logging
import uuid
from flask import session, url_for, render_template, request, flash, g, jsonify
from werkzeug.security import generate_password_hash
from speechwoz.db import get_db
from speechwoz import create_app

app = create_app()
AGENT_PROLIFIC_IDS = ["oplatek", "odusek"]

ROLE_AGENT = "ROLE_AGENT"
ROLE_CALLER = "ROLE_CALLER"


def get_annotator_info(session):
    # consider benefits storing infor to DB
    # info = get_db().execute("SELECT * FROM annotator WHERE id = ?", (ann_id,)).fetchone()
    ann_id = session.get("ann_id")
    return {
        "id": ann_id,
        "role": ROLE_AGENT if ann_id in AGENT_PROLIFIC_IDS else ROLE_CALLER,
        "accepted_terms": session.get("accepted_terms", False),
    }


@app.before_request
def load_logged_in_user():
    """If a user id is stored in the session, load the user object from
    the database into ``g.user``."""
    g.annotator_info = get_annotator_info(session)


@app.route("/logout")
def logout():
    """Clear the current session, including the stored user id."""
    session.clear()


@app.route("/", methods=["GET", "POST"])
def index():
    args = request.args.to_dict()

    # https://researcher-help.prolific.co/hc/en-gb/articles/360009224113-Qualtrics-integration-guide#heading-1
    prolific_pid = args.get("PROLIFIC_PID")
    prolific_studyid = args.get("STUDY_ID")
    prolific_sessionid = args.get("SESSION_ID")

    ann_id = session.get("ann_id")
    if ann_id is None:
        if prolific_pid is not None:
            ann_id = prolific_pid
            ann_id = generate_password_hash(ann_id)
            session["ann_id"] = ann_id
        else:
            msg = "Your PROLIFIC_PID argument is not set"
            flash(msg)
            logging.warning(msg)

    session["prolific_sessionid"] = prolific_sessionid
    session["prolific_studyid"] = prolific_studyid
    return render_template("index.html")


@app.route("/annotate")
def annotate():
    return render_template("annotate.html")


@app.route("/upload_recording/<source>", methods=["POST"])
def upload_recording(source):
    # check if the post request has the file part
    assert source in ["onboarding"]  # TODO add others
    if "file" not in request.files:
        return jsonify(status="no-file")
    file = request.files["file"]
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == "":
        flash("No selected file")
        return jsonify(status="no-filename")
    file_name = session["ann_id"] + str(uuid.uuid4()) + ".mp3"
    appdir = Path(os.path.dirname(os.path.realpath(__file__)))
    local_suffix = f"recordings/{source}/{file_name}"
    localpath = appdir / 'static' / local_suffix
    audio_url = url_for("static", filename=local_suffix)
    logging.info(f"Saving to {localpath}\n\t accessible at {audio_url}")
    file.save(localpath)
    # TODO add to DB
    # TODO save as wav
    return jsonify(status="ok", path=audio_url)
