from flask import session, redirect, url_for, render_template, request
from . import main
from .forms import LoginForm


@main.route('/', methods=['GET', 'POST'])
def index():
    """Login form to enter a room."""
    session['name'] = "1"
    session['room'] = "room1"

    form = LoginForm()
    if form.validate_on_submit():
        session['name'] = form.name.data
        session['room'] = form.room.data
        # redirect_value =  redirect(url_for('main.chat'))
        # print(redirect_value)
        # return redirect(redirect_value)
        return render_template('continue.html', room=session['room'], name=session['name'])
    elif request.method == 'GET':
        form.name.data = session.get('name', '')
        form.room.data = session.get('room', '')
    return render_template('index.html', form=form)


@main.route('/chat')
def chat():
    """Chat room. The user's name and room must be stored in
    the session."""
    name = session.get('name', '')
    room = session.get('room', '')
    if name == '' or room == '':
        return redirect(url_for('main.index'))
    return render_template('chat.html', name=name, room=room)
